"""Deterministic reasoning core: detection, loss math, health model, priority.

Design rule (per the case study): detection and all *numbers* come from
deterministic logic over telemetry. Natural-language explanations are
composed in ai.py from these computed facts — the reasoning layer never
invents data.

Detection pipeline, per telemetry tick:
    telemetry -> detectors -> loss estimation -> severity/priority
              -> alert upsert -> auto-dispatch ticket -> health model

Writer ownership: the simulator owns telemetry generation for the whole
fleet. POST /telemetry may inject *external* events for any device; while
external writes are arriving for a device, the simulator holds that
device's writer slot so the two streams never interleave in one history.
External streams that stop are re-owned by the simulator automatically.
"""
from __future__ import annotations

import statistics
from typing import Dict, List, Optional, Tuple

from . import ai
from .fusion import (
    compute_sensor_fusion_confidence,
    evaluate_sensor_diagnostics,
    get_contextual_baseline_flow,
)
from .ml import compute_anomaly_score, FAILURE_MODEL
from .state import (
    Alert,
    IncidentIntelligence,
    LITERS_PER_FLUSH,
    MaintenanceTicket,
    Store,
    TelemetryEvent,
    utcnow,
)

# ---------------------------------------------------------------- constants

LEAK_MIN_FLOW = 0.2          # L/min considered "flowing" when idle
LEAK_MIN_DURATION = 5        # simulated minutes of sustained idle flow
PHANTOM_FLUSH_WINDOW = 10    # ticks
PHANTOM_FLUSH_MIN_EVENTS = 3
SENSOR_FAULT_MIN_ERRORS = 3  # in recent window
IDLE_FLOW_ALERTABLE = 0.15   # idle flow (occupancy 0, no flush) that counts

SEVERITY_BY_DAILY_LOSS = [(2500, "CRITICAL"), (1000, "HIGH"), (250, "MEDIUM")]
PRIORITY_BY_SEVERITY = {"CRITICAL": "P1", "HIGH": "P2", "MEDIUM": "P3", "LOW": "P4"}

TECHNICIAN_ROSTER = [
    {"name": "Arjun Sharma", "cert": "Plumbing", "zone": "Terminal 2", "active_tickets": 1},
    {"name": "Priya Nair", "cert": "Electrical/IoT", "zone": "Terminal 1", "active_tickets": 0},
    {"name": "Ramesh Patil", "cert": "General Facility", "zone": "Terminal 3", "active_tickets": 0},
    {"name": "Sunita Rao", "cert": "Housekeeping", "zone": "Terminal 2", "active_tickets": 0},
]


def optimize_dispatch(alert: Alert) -> dict:
    """SLA-aware technician assignment matching certification, proximity, and queue load."""
    sla_min = 15 if alert.priority == "P1" else (45 if alert.priority == "P2" else (90 if alert.priority == "P3" else 180))
    if alert.kind in ("continuous_leak", "phantom_flush", "pressure_anomaly"):
        needed = "Plumbing"
    elif alert.kind in ("sensor_fault", "predictive"):
        needed = "Electrical/IoT"
    elif alert.kind == "hygiene":
        needed = "Housekeeping"
    else:
        needed = "General Facility"

    candidates = [t for t in TECHNICIAN_ROSTER if t["cert"] == needed or t["cert"] == "General Facility"]
    candidates.sort(key=lambda t: (t["zone"] not in alert.zone, t["active_tickets"]))
    tech = candidates[0] if candidates else TECHNICIAN_ROSTER[0]
    eta = 8 if tech["zone"] in alert.zone else 16

    return {
        "technician": tech["name"],
        "team": tech["cert"],
        "sla_deadline_minutes": sla_min,
        "eta_minutes": eta,
        "rationale": f"✓ {tech['cert']} Certified · ✓ Based in {tech['zone']} · ✓ Active queue: {tech['active_tickets']} · ✓ {sla_min}m SLA",
    }

# External /telemetry writes take over a device's writer slot while they
# keep arriving; the simulator pauses that device and resumes it after
# EXTERNAL_WRITE_TTL_TICKS of silence from the external stream.
EXTERNAL_WRITE_TTL_TICKS = 5


def severity_from_daily_loss(daily_loss: float) -> str:
    for threshold, sev in SEVERITY_BY_DAILY_LOSS:
        if daily_loss >= threshold:
            return sev
    return "LOW"


# ------------------------------------------------------------ event intake

def _advance_sla_timers(store: Store) -> None:
    """Advance countdown timers for active alerts, tickets, and canonical incidents."""
    for alert in store.alerts:
        if alert.status == "OPEN":
            alert.sla_remaining_seconds = max(0, alert.sla_remaining_seconds - 60)
            if alert.sla_remaining_seconds <= 300:
                alert.sla_breach_risk = "CRITICAL"
            elif alert.sla_remaining_seconds <= 600:
                alert.sla_breach_risk = "HIGH"
            elif alert.sla_remaining_seconds <= 1200:
                alert.sla_breach_risk = "MEDIUM"
            else:
                alert.sla_breach_risk = "LOW"

    for ticket in store.tickets:
        if ticket.status == "OPEN":
            ticket.sla_remaining_seconds = max(0, ticket.sla_remaining_seconds - 60)
            if ticket.sla_remaining_seconds <= 300:
                ticket.sla_breach_risk = "CRITICAL"
            elif ticket.sla_remaining_seconds <= 600:
                ticket.sla_breach_risk = "HIGH"
            elif ticket.sla_remaining_seconds <= 1200:
                ticket.sla_breach_risk = "MEDIUM"
            else:
                ticket.sla_breach_risk = "LOW"

    for inc in store.incidents:
        if inc.status == "OPEN":
            inc.sla_remaining_seconds = max(0, inc.sla_remaining_seconds - 60)
            if inc.sla_remaining_seconds <= 300:
                inc.sla_breach_risk = "CRITICAL"
            elif inc.sla_remaining_seconds <= 600:
                inc.sla_breach_risk = "HIGH"
            elif inc.sla_remaining_seconds <= 1200:
                inc.sla_breach_risk = "MEDIUM"
            else:
                inc.sla_breach_risk = "LOW"


def process_events(store: Store, events: List[TelemetryEvent], external: bool = False) -> dict:
    """Run the full detection pipeline over one batch of telemetry.

    external=True marks events arriving via POST /telemetry: they claim the
    writer slot for their devices and the detection/hygiene/health passes
    run immediately instead of waiting for the next simulator tick.
    """
    new_alerts: List[Alert] = []
    updated_alerts: List[Alert] = []
    new_tickets: List[MaintenanceTicket] = []

    _advance_sla_timers(store)

    if external:
        touched = {ev.device_id for ev in events if ev.device_id in store.devices}
        for device_id in touched:
            store.external_writes[device_id] = store.tick_count
            store.hold_writers.add(device_id)

    consumed = 0.0
    for ev in events:
        dev = store.devices.get(ev.device_id)
        if dev is None:
            continue  # external events for unknown devices are ignored
        consumed += ev.flush_count * LITERS_PER_FLUSH + ev.flow_lpm
        _record(store, dev, ev)

    store.consumed_today_liters += consumed

    for ev in events:
        dev = store.devices.get(ev.device_id)
        if dev is None:
            continue
        alert, ticket, updated = _detect(store, dev)
        if alert:
            new_alerts.append(alert)
        if ticket:
            new_tickets.append(ticket)
        if updated:
            updated_alerts.append(updated)

    _detect_hygiene(store)
    _decay_health(store)
    if not external:
        _append_timeseries(store)
    store.dirty = True
    return {"new_alerts": new_alerts, "updated_alerts": updated_alerts,
            "new_tickets": new_tickets}


def _record(store: Store, dev, ev: TelemetryEvent) -> None:
    dev.flow_lpm = ev.flow_lpm
    dev.occupancy = ev.occupancy
    dev.flush_count = ev.flush_count
    dev.duration_min = ev.duration_min
    dev.sensor_errors = max(dev.sensor_errors, ev.sensor_errors)
    dev.battery_pct = ev.battery_pct
    dev.pressure_bar = getattr(ev, "pressure_bar", 3.0)
    dev.history.append({
        "t": ev.timestamp.isoformat(),
        "flow": ev.flow_lpm,
        "occ": ev.occupancy,
        "flush": ev.flush_count,
        "err": ev.sensor_errors,
    })
    anom = compute_anomaly_score(
        flow_lpm=dev.flow_lpm,
        expected_flow_lpm=dev.expected_flow_lpm,
        occupancy=dev.occupancy,
        flush_count=dev.flush_count,
        duration_min=dev.duration_min,
        sensor_errors=dev.sensor_errors,
        flow_variance_pct=dev.flow_variance_pct,
        pressure_bar=dev.pressure_bar,
    )
    dev.anomaly_score = anom["score"]
    dev.anomaly_band = anom["band"]
    dev.contributing_factors = anom["factors"]
    store.telemetry.append(ev.model_dump(mode="json"))


def _expire_external_writers(store: Store) -> None:
    """Simulator-side tick hook: reclaim writer slots from external streams
    that went quiet, so devices return to normal simulation."""
    stale = [d for d, tick in store.external_writes.items()
             if store.tick_count - tick > EXTERNAL_WRITE_TTL_TICKS]
    for d in stale:
        store.external_writes.pop(d, None)
        store.hold_writers.discard(d)


# ---------------------------------------------------------------- detectors

def _idle_flow_mean(dev) -> float:
    idle = [h["flow"] for h in dev.history
            if h["flush"] == 0 and h["occ"] == 0]
    return statistics.mean(idle) if idle else 0.0


def _flow_variance_pct(dev) -> float:
    flows = [h["flow"] for h in dev.history]
    if len(flows) < 5:
        return 0.0
    mean_nonzero = statistics.mean([f for f in flows if f > 0.1] or [0.0])
    denom = max(1.0, dev.expected_flow_lpm or mean_nonzero)
    return min(150.0, statistics.stdev(flows) / denom * 100.0)


def _detect(store: Store, dev) -> Tuple[Optional[Alert], Optional[MaintenanceTicket], Optional[Alert]]:
    """Return (new_alert, new_ticket, updated_alert)."""
    recent = list(dev.history)[-PHANTOM_FLUSH_WINDOW:]

    # ---- Detector 1: continuous leak (flow while idle & unoccupied) ----
    idle_flow = _idle_flow_mean(dev)
    last = dev.history[-1] if dev.history else None
    if last and last["flow"] > LEAK_MIN_FLOW and last["occ"] == 0 and last["flush"] == 0:
        dev.episode_min += 1
    else:
        dev.episode_min = 0

    if last and last["flow"] > LEAK_MIN_FLOW and last["occ"] == 0 \
            and last["flush"] == 0 and dev.episode_min >= LEAK_MIN_DURATION:
        daily = round(last["flow"] * 1440, 1)
        return _upsert_alert(
            store, dev, kind="continuous_leak",
            issue="Continuous water flow detected without occupancy or flush events",
            loss_so_far=round(last["flow"] * dev.episode_min, 1),
            daily_loss=daily,
            telemetry_snapshot={
                "flow_lpm": last["flow"], "occupancy": last["occ"],
                "flush_count": last["flush"], "duration_min": dev.episode_min,
                "expected_flow_lpm": 0.0,
            },
        )

    # ---- Detector 2: phantom flushes (flush events with zero occupancy) ----
    phantom = sum(h["flush"] for h in recent if h["occ"] == 0)
    if phantom >= PHANTOM_FLUSH_MIN_EVENTS:
        rate_per_min = phantom / len(recent) if recent else 0.0
        daily = round(rate_per_min * LITERS_PER_FLUSH * 1440, 1)
        return _upsert_alert(
            store, dev, kind="phantom_flush",
            issue="Abnormal flush pattern — flush events with zero occupancy",
            loss_so_far=round(phantom * LITERS_PER_FLUSH, 1),
            daily_loss=daily,
            telemetry_snapshot={
                "flush_events_zero_occupancy": phantom,
                "window_ticks": len(recent),
                "estimated_flush_rate_per_min": round(rate_per_min, 2),
            },
        )

    # ---- Detector 3: sensor fault (flatline signature) ----
    # Requires a dead flow signal, not just error ticks: a degrading device
    # also throws sensor errors while still reporting intermittent micro-flows,
    # and that case belongs to the predictive health model instead.
    err_events = sum(1 for h in recent if h["err"] > 0)
    if err_events >= SENSOR_FAULT_MIN_ERRORS and _idle_flow_mean(dev) < 0.01:
        return _upsert_alert(
            store, dev, kind="sensor_fault",
            issue="Telemetry degradation — repeated sensor errors / flatlined readings",
            loss_so_far=0.0, daily_loss=0.0,
            telemetry_snapshot={
                "sensor_error_ticks": err_events,
                "battery_pct": round(dev.battery_pct, 1),
                "last_flow": dev.flow_lpm,
            },
        )

    # ---- Detector 4: predictive (health model) — suppressed only while an
    # acute water-loss incident is already explaining a device whose health
    # was never independently degraded (an acute leak dragging health down
    # needs no second alert). Wear that degraded health on its own always
    # earns the predictive flag, even after a leak develops from it.
    has_loss_alert = any(
        a.device_id == dev.device_id and a.status == "OPEN"
        and a.kind in ("continuous_leak", "phantom_flush")
        for a in store.alerts
    )
    # Fires early in the MEDIUM->HIGH transition (health < 55) so a wearing
    # device is flagged BEFORE its degradation ripens into a sustained leak —
    # that race is the whole predictive-maintenance story.
    if dev.risk == "HIGH" and dev.health_score < 55 and not (
        has_loss_alert and not dev.health_degraded_once
    ):
        return _upsert_alert(
            store, dev, kind="predictive",
            issue="Predicted failure risk — device health degraded",
            loss_so_far=0.0, daily_loss=0.0,
            telemetry_snapshot={
                "health_score": dev.health_score,
                "failure_probability_7d": round(dev.failure_probability, 2),
                "flow_variance_pct": round(dev.flow_variance_pct, 1),
                "idle_flow_lpm": round(idle_flow, 2),
                "sensor_errors": dev.sensor_errors,
            },
        )
    return None, None, None


def _detect_hygiene(store: Store) -> None:
    spike = store.scenarios.get("occupancy-spike")
    spike_zone = spike.get("zone_id") if spike else None
    usage_mult = spike.get("usage_mult", 1.0) if spike else 1.0
    for zone in store.zones.values():
        zone_devices = [d for d in store.devices.values() if d.zone_id == zone.zone_id]
        interactions = sum(d.flush_count for d in zone_devices) + zone.occupancy / 2
        if zone.zone_id == spike_zone:
            interactions *= usage_mult
        zone.usage_since_cleaning += interactions
        # adaptive threshold: base × occupancy pressure × time-since-clean
        # pressure. The occupancy term adapts to *sustained* demand (capped at
        # +25%) so a transient surge raises usage faster than it raises the bar.
        occupancy_pressure = 1.0 + min(0.25, max(0.0, zone.occupancy / max(1, zone.base_population) - 1.0) * 0.25)
        staleness_pressure = 1.0 + min(0.35, zone.last_cleaned_min_ago / 720.0)
        adaptive_threshold = int(zone.threshold * max(0.8, occupancy_pressure * staleness_pressure))
        zone.adaptive_threshold = adaptive_threshold
        # require a 3% margin so the alert carries a meaningful over-target story
        breach = zone.usage_since_cleaning >= adaptive_threshold * 1.03
        if breach and not zone.cleaning_required:
            zone.cleaning_required = True
            _raise_hygiene_alert(store, zone, adaptive_threshold)
        elif not breach:
            zone.cleaning_required = False


def _raise_hygiene_alert(store: Store, zone, threshold: int) -> None:
    # one hygiene alert per zone unless the previous one is resolved
    existing = next((a for a in store.alerts
                     if a.kind == "hygiene" and a.zone == zone.name and a.status == "OPEN"), None)
    if existing:
        return
    flow_meter = next((d for d in store.devices.values()
                       if d.zone_id == zone.zone_id and d.type == "Toilet"), None)
    device_id = flow_meter.device_id if flow_meter else zone.zone_id
    over_pct = round((zone.usage_since_cleaning / max(1, threshold) - 1) * 100, 1)
    diagnosis = ai.compose_diagnosis("hygiene", {
        "zone": zone.name,
        "usage": zone.usage_since_cleaning,
        "threshold": threshold,
        "over_pct": max(0.0, over_pct),
        "occupancy": zone.occupancy,
        "last_cleaned_min_ago": zone.last_cleaned_min_ago,
    })
    alert = Alert(
        id=_next_alert_id(store),
        device_id=device_id, device_type="Zone Hygiene", zone=zone.name,
        kind="hygiene", issue="Cleaning required — usage threshold exceeded",
        severity="MEDIUM", priority="P3",
        estimated_loss_liters=0.0, estimated_daily_loss_liters=0.0,
        estimated_monthly_loss_liters=0.0,
        diagnosis=diagnosis["diagnosis"],
        recommended_action=diagnosis["recommended_action"],
        telemetry={
            "usage_since_cleaning": zone.usage_since_cleaning,
            "adaptive_threshold": threshold,
            "occupancy": zone.occupancy,
            "minutes_since_cleaning": zone.last_cleaned_min_ago,
        },
    )
    store.alerts.append(alert)
    # housekeeping ticket only when the breach is significant (>15% over threshold)
    if zone.usage_since_cleaning >= threshold * 1.15:
        _dispatch_ticket(store, alert)
    return alert


# ------------------------------------------------------------- alert logic

def _next_alert_id(store: Store) -> str:
    aid = f"ALT-{store.alert_seq:05d}"
    store.alert_seq += 1
    return aid


def _upsert_alert(store: Store, dev, kind: str, issue: str, loss_so_far: float,
                  daily_loss: float, telemetry_snapshot: dict) -> Tuple[Optional[Alert], Optional[MaintenanceTicket], Optional[Alert]]:
    if daily_loss > 0:
        severity = severity_from_daily_loss(daily_loss)
    else:
        severity = "HIGH" if kind == "predictive" else "MEDIUM"
    priority = PRIORITY_BY_SEVERITY[severity]
    existing = next((a for a in store.alerts
                     if a.device_id == dev.device_id and a.kind == kind and a.status == "OPEN"), None)

    if existing:
        changed = False
        if not existing.before_state:
            existing.before_state = {
                "flow_lpm": round(dev.flow_lpm, 2),
                "pressure_bar": round(getattr(dev, "pressure_bar", 3.0), 2),
                "anomaly_score": getattr(dev, "anomaly_score", 80),
                "leak_confidence": getattr(existing, "leak_confidence", 0.95),
            }
            changed = True
        inc = next((i for i in store.incidents if i.incident_id == f"INC-{existing.id}" or (i.device_id == existing.device_id and i.status == "OPEN")), None)
        if not inc:
            inc = IncidentIntelligence(
                incident_id=f"INC-{existing.id}",
                device_id=dev.device_id,
                device_type=dev.type,
                zone=dev.zone,
                terminal=dev.terminal,
                kind=kind,
                severity=existing.severity,
                priority=existing.priority,
                leak_confidence=existing.leak_confidence,
                sensor_confidence=existing.sensor_confidence,
                root_cause=existing.root_cause,
                root_cause_confidence=existing.root_cause_confidence,
                estimated_loss_lpd=existing.estimated_daily_loss_liters,
                estimated_monthly_loss_liters=existing.estimated_monthly_loss_liters,
                sla_minutes=existing.sla_minutes,
                sla_remaining_seconds=existing.sla_remaining_seconds,
                sla_breach_risk=existing.sla_breach_risk,
                assigned_technician=existing.assigned_technician or "Arjun Sharma (Plumbing)",
                recommended_action=existing.recommended_action,
                status="OPEN",
                before_state=existing.before_state,
                after_state=None,
                timeline=list(existing.timeline),
                created_at=existing.created_at,
            )
            store.incidents.append(inc)

        if daily_loss != existing.estimated_daily_loss_liters:
            existing.estimated_daily_loss_liters = daily_loss
            existing.estimated_monthly_loss_liters = round(daily_loss * 30, 1)
            changed = True
        if loss_so_far > existing.estimated_loss_liters:
            existing.estimated_loss_liters = loss_so_far
            changed = True
        new_sev = severity_from_daily_loss(daily_loss) if daily_loss > 0 else severity
        if new_sev != existing.severity and _sev_rank(new_sev) > _sev_rank(existing.severity):
            existing.severity = new_sev
            existing.priority = PRIORITY_BY_SEVERITY[new_sev]
            existing.diagnosis = ai.compose_diagnosis(kind, _facts(store, dev, existing, telemetry_snapshot))["diagnosis"]
            changed = True
        if changed:
            existing.telemetry = telemetry_snapshot
            existing.diagnosis = ai.compose_diagnosis(kind, _facts(store, dev, existing, telemetry_snapshot))["diagnosis"]
            existing.updated_at = utcnow()
            # keep the auto-generated dispatch ticket in sync with escalation
            for t in store.tickets:
                if t.alert_id == existing.id and t.status == "OPEN":
                    t.estimated_water_loss_daily_liters = existing.estimated_daily_loss_liters
                    t.severity = existing.severity
                    t.priority = existing.priority
            return None, None, existing
        return None, None, None

    facts = _facts(store, dev, None, telemetry_snapshot)
    composed = ai.compose_diagnosis(kind, facts)
    anom_score = getattr(dev, "anomaly_score", 80)
    anom_band = getattr(dev, "anomaly_band", "CRITICAL")
    recent_window = list(dev.history)[-10:]

    diag = evaluate_sensor_diagnostics(
        flow_lpm=dev.flow_lpm,
        occupancy=dev.occupancy,
        flush_count=dev.flush_count,
        sensor_errors=dev.sensor_errors,
        battery_pct=dev.battery_pct,
        history_window=recent_window,
    )
    sensor_conf = diag["overall_telemetry_confidence"]

    now = utcnow()
    baseline = get_contextual_baseline_flow(dev.zone, dev.terminal, now.hour)

    fusion = compute_sensor_fusion_confidence(
        flow_lpm=dev.flow_lpm,
        expected_baseline_lpm=baseline,
        occupancy=dev.occupancy,
        flush_count=dev.flush_count,
        duration_min=dev.duration_min,
        flow_variance_pct=dev.flow_variance_pct,
        pressure_bar=getattr(dev, "pressure_bar", 3.0),
        sensor_confidence=sensor_conf,
        history_flows=[h["flow"] for h in recent_window],
    )
    leak_conf = round(fusion["leak_confidence_pct"] / 100.0, 2)
    root_cause = fusion["root_cause"]
    root_cause_conf = fusion["root_cause_confidence"]
    sla_min = 15 if priority == "P1" else (45 if priority == "P2" else (90 if priority == "P3" else 180))

    alert = Alert(
        id=_next_alert_id(store),
        device_id=dev.device_id, device_type=dev.type, zone=dev.zone,
        kind=kind, issue=issue,
        severity=severity, priority=priority,
        estimated_loss_liters=loss_so_far,
        estimated_daily_loss_liters=round(daily_loss, 1),
        estimated_monthly_loss_liters=round(daily_loss * 30, 1),
        diagnosis=composed["diagnosis"],
        recommended_action=composed["recommended_action"],
        telemetry=telemetry_snapshot,
        anomaly_score=anom_score,
        anomaly_band=anom_band,
        leak_confidence=leak_conf,
        sensor_confidence=sensor_conf,
        root_cause=root_cause,
        root_cause_confidence=root_cause_conf,
        sla_minutes=sla_min,
        sla_remaining_seconds=sla_min * 60,
        sla_breach_risk="LOW",
        before_state={
            "flow_lpm": round(dev.flow_lpm, 2),
            "pressure_bar": round(getattr(dev, "pressure_bar", 3.0), 2),
            "anomaly_score": anom_score,
            "leak_confidence": leak_conf,
        },
        timeline=[
            {"time": now.strftime("%H:%M UTC"), "event": "ANOMALY_CONFIRMED", "note": f"Triggered {kind} ({issue})"}
        ],
    )
    store.alerts.append(alert)
    ticket = _dispatch_ticket(store, alert)

    # Canonical Incident record
    incident = IncidentIntelligence(
        incident_id=f"INC-{alert.id}",
        device_id=dev.device_id,
        device_type=dev.type,
        zone=dev.zone,
        terminal=dev.terminal,
        kind=kind,
        severity=severity,
        priority=priority,
        leak_confidence=leak_conf,
        sensor_confidence=sensor_conf,
        root_cause=root_cause,
        root_cause_confidence=root_cause_conf,
        estimated_loss_lpd=round(daily_loss, 1),
        estimated_monthly_loss_liters=round(daily_loss * 30, 1),
        sla_minutes=sla_min,
        sla_remaining_seconds=sla_min * 60,
        sla_breach_risk="LOW",
        assigned_technician=ticket.assigned_technician if ticket and ticket.assigned_technician else "Arjun Sharma (Plumbing)",
        recommended_action=composed["recommended_action"],
        status="OPEN",
        before_state=alert.before_state,
        after_state=None,
        timeline=list(alert.timeline),
        created_at=alert.created_at,
    )
    store.incidents.append(incident)
    return alert, ticket, None


def _sev_rank(sev: str) -> int:
    return {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}[sev]


def _facts(store: Store, dev, alert: Optional[Alert], snap: dict) -> dict:
    facts = {
        "device_id": dev.device_id,
        "device_type": dev.type,
        "zone": dev.zone,
        "occupancy": dev.occupancy,
        "flow_lpm": dev.flow_lpm,
        "flush_count": dev.flush_count,
        "expected_flow_lpm": dev.expected_flow_lpm,
        "duration_min": dev.duration_min,
        "health_score": dev.health_score,
        "failure_probability": round(dev.failure_probability, 2),
        "flow_variance_pct": round(dev.flow_variance_pct, 1),
        "anomaly_frequency": dev.anomaly_frequency,
        "flush_irregularity": dev.flush_irregularity,
        "sensor_errors": dev.sensor_errors,
        "battery_pct": round(dev.battery_pct, 1),
        "daily_loss": 0.0,
        "monthly_loss": 0.0,
        "loss_so_far": 0.0,
    }
    if alert is not None:
        facts["daily_loss"] = alert.estimated_daily_loss_liters
        facts["monthly_loss"] = alert.estimated_monthly_loss_liters
        facts["loss_so_far"] = alert.estimated_loss_liters
    facts.update(snap)
    return facts


# ------------------------------------------------------- auto-dispatch

def _dispatch_ticket(store: Store, alert: Alert) -> Optional[MaintenanceTicket]:
    rules = {
        "continuous_leak": ("Plumbing / Water Waste",
                            "Inspect flush valve and inlet mechanism; replace cartridge seal."),
        "phantom_flush": ("Plumbing / Flush Mechanism",
                          "Inspect solenoid and flush sensor calibration; reset valve actuator."),
        "sensor_fault": ("Instrumentation / IoT",
                          "Replace sensor node, verify wiring and recalibrate."),
        "hygiene": ("Housekeeping",
                    "Deploy cleaning crew; deep-clean fixtures and restock consumables."),
        "predictive": ("Predictive Maintenance",
                        "Schedule preventive inspection within 72 hours; check seals and actuator wear."),
        "pressure_anomaly": ("Mechanical & Supply",
                              "Inspect main line isolation valve and check booster pump regulator."),
    }
    if alert.kind not in rules:
        return None
    category, action = rules[alert.kind]
    opt = optimize_dispatch(alert)

    alert.assigned_technician = opt["technician"]
    alert.sla_minutes = opt["sla_deadline_minutes"]
    alert.timeline.append({
        "time": utcnow().strftime("%H:%M UTC"),
        "event": "DISPATCH_OPTIMIZED",
        "note": f"Auto-assigned {opt['technician']} ({opt['team']}) — {opt['sla_deadline_minutes']}m SLA",
    })

    ticket = MaintenanceTicket(
        ticket_id=f"KHL-{store.ticket_seq}",
        category=category,
        asset=alert.device_id,
        location=alert.zone,
        issue=alert.issue,
        severity=alert.severity,
        priority=alert.priority,
        estimated_water_loss_daily_liters=alert.estimated_daily_loss_liters,
        action=action,
        ai_summary=ai.compose_ticket_summary(alert),
        alert_id=alert.id,
        assigned_technician=opt["technician"],
        technician_team=opt["team"],
        sla_deadline_minutes=opt["sla_deadline_minutes"],
        sla_remaining_seconds=opt["sla_deadline_minutes"] * 60,
        sla_breach_risk="LOW",
        eta_minutes=opt["eta_minutes"],
        dispatch_rationale=opt["rationale"],
        timeline=[
            {"time": utcnow().strftime("%H:%M UTC"), "event": "DISPATCH_OPTIMIZED", "note": opt["rationale"]}
        ],
    )
    store.ticket_seq += 1
    store.tickets.append(ticket)
    return ticket


# ------------------------------------------------------------ health model

def _decay_health(store: Store) -> None:
    """Recompute device health scores and evaluate ML failure-risk model."""
    for dev in store.devices.values():
        if len(dev.history) < 8:
            continue
        recent = list(dev.history)[-30:]
        window = len(recent)

        idle = _idle_flow_mean(dev)
        anomaly_ticks = sum(
            1 for h in recent
            if h["flush"] == 0 and h["occ"] == 0 and h["flow"] > IDLE_FLOW_ALERTABLE
        )
        irregular = sum(1 for h in recent if h["flush"] > 0 and h["occ"] == 0)

        dev.anomaly_frequency = anomaly_ticks
        dev.flush_irregularity = irregular
        dev.flow_variance_pct = _flow_variance_pct(dev)

        penalty = 0.0
        penalty += min(28, (anomaly_ticks / window) * 100 * 0.45)
        penalty += min(36, idle * 32.0)
        penalty += min(15, irregular * 3.0)
        penalty += min(20, dev.sensor_errors * 1.6)
        dev.health_score = int(max(0, min(100, round(100 - penalty))))

        # Evaluate ML predictive failure risk
        pred = FAILURE_MODEL.predict(dev)
        dev.failure_probability = pred["failure_probability_7d"]
        dev.risk = pred["risk"]
        dev.contributing_factors = pred["contributing_factors"]

        if dev.health_score < 75:
            dev.health_degraded_once = True
            dev.risk = "LOW"
        elif dev.health_score >= 45:
            dev.risk = "MEDIUM"
        else:
            dev.risk = "HIGH"


# ------------------------------------------------------------- resolution

def resolve_alert(store: Store, alert_id: str) -> Optional[Alert]:
    clean_id = alert_id.replace("INC-", "")
    alert = next((a for a in store.alerts if (a.id == clean_id or a.id == alert_id or a.device_id == alert_id) and a.status == "OPEN"), None)
    if not alert:
        return None
    alert.status = "RESOLVED"
    alert.resolved_at = utcnow()
    duration_min = (alert.resolved_at - alert.created_at).total_seconds() / 60.0
    alert.resolution_note = ai.compose_resolution_note(alert, store)
    alert.timeline.append({
        "time": alert.resolved_at.strftime("%H:%M UTC"),
        "event": "VERIFIED_RESOLUTION",
        "note": f"Repair verified. Conserved {alert.estimated_monthly_loss_liters:,.0f} L/month.",
    })
    dev = store.devices.get(alert.device_id)
    alert.after_state = {
        "flow_lpm": dev.flow_lpm if dev else 0.0,
        "pressure_bar": round(getattr(dev, "pressure_bar", 3.0), 2) if dev else 3.0,
        "anomaly_score": 0,
        "leak_confidence": 0.02,
        "verified_savings_monthly_l": alert.estimated_monthly_loss_liters,
    }
    for inc in store.incidents:
        if inc.incident_id == f"INC-{alert.id}" or (inc.device_id == alert.device_id and inc.status == "OPEN"):
            inc.status = "RESOLVED"
            inc.resolved_at = alert.resolved_at
            inc.after_state = alert.after_state
            inc.timeline.append({
                "time": alert.resolved_at.strftime("%H:%M UTC"),
                "event": "VERIFIED_RESOLUTION",
                "note": alert.resolution_note,
            })
    if alert.kind in ("continuous_leak", "phantom_flush"):
        store.saved_month_liters += alert.estimated_monthly_loss_liters
    store.resolved_count += 1
    store.resolved_durations_min.append(round(duration_min, 1))

    for t in store.tickets:
        if t.alert_id == alert.id and t.status == "OPEN":
            t.status = "RESOLVED"
            t.resolved_at = alert.resolved_at
            t.timeline.append({
                "time": alert.resolved_at.strftime("%H:%M UTC"),
                "event": "TICKET_VERIFIED_CLOSED",
                "note": alert.resolution_note,
            })
            t.resolved_at = alert.resolved_at

    dev = store.devices.get(alert.device_id)
    if dev:
        serviced = alert.kind in ("continuous_leak", "phantom_flush", "predictive")
        if serviced:
            # leak/phantom: repair verified; predictive: preventive inspection
            # completed — either way the health model restarts from baseline.
            _service_reset(dev)
        elif alert.kind == "sensor_fault":
            # repaired/replaced node: errors and stale readings cleared
            dev.sensor_errors = 0
            dev.battery_pct = 100.0
        _end_scenario(store, dev.device_id)
        if serviced:
            # A physical repair closes every open water-loss incident on that
            # fixture — bank their savings too, or the ledger understates the
            # visit and stale alerts linger after the fix.
            for other in store.alerts:
                if (other.device_id == dev.device_id and other.id != alert.id
                        and other.status == "OPEN"
                        and other.kind in ("continuous_leak", "phantom_flush")):
                    other.status = "RESOLVED"
                    other.resolved_at = alert.resolved_at
                    other.resolution_note = (
                        f"Closed by service visit for {alert.id} "
                        f"({alert.kind.replace('_', ' ')}): fixture repaired, "
                        f"telemetry verified back to baseline."
                    )
                    store.saved_month_liters += other.estimated_monthly_loss_liters
                    for t in store.tickets:
                        if t.alert_id == other.id and t.status == "OPEN":
                            t.status = "RESOLVED"
                            t.resolved_at = alert.resolved_at
    store.dirty = True
    return alert


def _service_reset(dev) -> None:
    """Post-repair baseline: telemetry history clears and the health model
    starts fresh, so a just-fixed device is not immediately flagged by the
    predictive layer on its own stale history."""
    dev.history.clear()
    dev.flow_lpm = 0.0
    dev.episode_min = 0
    dev.sensor_errors = 0
    dev.health_score = 100
    dev.risk = "LOW"
    dev.failure_probability = 0.0
    dev.flow_variance_pct = 0.0
    dev.anomaly_frequency = 0
    dev.flush_irregularity = 0
    dev.health_degraded_once = False
    dev.history.append({"flow": 0.0, "occ": 0, "pressure": 3.0, "ts": utcnow().isoformat()})


def _end_scenario(store: Store, device_id: str) -> None:
    """A resolution is the authoritative fix: stop any scenario driving this
    device so the fault does not silently re-fire after the repair."""
    for kind in [k for k, sc in store.scenarios.items() if sc.get("device_id") == device_id]:
        del store.scenarios[kind]
    store.hold_writers.discard(device_id)


def resolve_ticket(store: Store, ticket_id: str) -> Optional[MaintenanceTicket]:
    ticket = next((t for t in store.tickets if t.ticket_id == ticket_id and t.status == "OPEN"), None)
    if not ticket:
        return None
    ticket.status = "RESOLVED"
    ticket.resolved_at = utcnow()
    if ticket.alert_id:
        alert = next((a for a in store.alerts if a.id == ticket.alert_id and a.status == "OPEN"), None)
        if alert:
            resolve_alert(store, alert.id)
    else:
        _end_scenario(store, ticket.asset)
    store.dirty = True
    return ticket


def record_cleaning(store: Store, zone_id: str) -> Optional[dict]:
    zone = store.zones.get(zone_id)
    if not zone:
        return None
    zone.usage_since_cleaning = 0
    zone.cleaning_required = False
    zone.last_cleaned_min_ago = 0
    event = {"zone_id": zone.zone_id, "zone": zone.name, "at": utcnow().isoformat()}
    store.cleaning_events.append(event)
    for a in store.alerts:
        if a.kind == "hygiene" and a.zone == zone.name and a.status == "OPEN":
            a.status = "RESOLVED"
            a.resolved_at = utcnow()
            a.resolution_note = (f"Cleaning completed for {zone.name}. Usage counter reset; "
                                 f"hygiene threshold monitoring continues.")
            for t in store.tickets:
                if t.alert_id == a.id and t.status == "OPEN":
                    t.status = "RESOLVED"
                    t.resolved_at = a.resolved_at
    store.dirty = True
    return event


# ---------------------------------------------------------------- snapshot

def _device_status(store: Store, dev) -> str:
    if dev.risk == "HIGH" or any(
        a.device_id == dev.device_id and a.status == "OPEN" and a.severity in ("HIGH", "CRITICAL")
        for a in store.alerts
    ):
        return "critical"
    if any(a.device_id == dev.device_id and a.status == "OPEN" and a.severity == "MEDIUM"
           for a in store.alerts):
        return "warning"
    if dev.battery_pct < 10:
        return "offline"
    return "normal"


def facility_snapshot(store: Store) -> dict:
    zones_out = []
    for zone in store.zones.values():
        zone_devices = [d for d in store.devices.values() if d.zone_id == zone.zone_id]
        dev_out = []
        for d in zone_devices:
            dev_out.append({
                "device_id": d.device_id, "type": d.type,
                "flow_lpm": round(d.flow_lpm, 2), "occupancy": d.occupancy,
                "flush_count": d.flush_count, "health_score": d.health_score,
                "risk": d.risk, "status": _device_status(store, d),
                "scenario": next((k for k, sc in store.scenarios.items()
                                  if sc.get("device_id") == d.device_id), None),
                "flow_series": [h["flow"] for h in list(d.history)[-24:]],
            })
        has_critical = any(x["status"] == "critical" for x in dev_out)
        status = "critical" if (has_critical or zone.cleaning_required and zone.usage_since_cleaning > zone.threshold * 1.1) else \
                 "warning" if (any(x["status"] == "warning" for x in dev_out) or zone.cleaning_required) else "normal"
        threshold = getattr(zone, "adaptive_threshold", zone.threshold)
        zones_out.append({
            **zone.to_dict(), "adaptive_threshold": threshold,
            "status": status,
            "devices": dev_out,
        })

    open_alerts = [a for a in store.alerts if a.status == "OPEN"]
    high_risk = [d for d in store.devices.values() if d.risk == "HIGH"]
    wastage = round(sum(a.estimated_loss_liters for a in open_alerts), 1)
    mttr = (round(sum(store.resolved_durations_min) / len(store.resolved_durations_min), 1)
            if store.resolved_durations_min else 0.0)
    avg_health = round(sum(d.health_score for d in store.devices.values()) / max(1, len(store.devices)), 1)

    open_tickets = [t for t in store.tickets if t.status == "OPEN"]
    return {
        "facility": {
            "name": "Pune International Airport",
            "manager": "AquaGuard Operations Center",
            "status": "Operational",
            "zones": len(store.zones),
            "devices": len(store.devices),
            "sim_minutes_elapsed": store.tick_count,
        },
        "kpis": {
            "water_consumption_liters": round(store.consumed_today_liters, 1),
            "active_alerts": len(open_alerts),
            "critical_alerts": sum(1 for a in open_alerts if a.severity in ("HIGH", "CRITICAL")),
            "devices_at_risk": len(high_risk),
            "water_saved_month_liters": round(store.saved_month_liters, 1),
            "current_wastage_liters": wastage,
            "incidents_resolved": store.resolved_count,
            "mttr_minutes": mttr,
            "avg_device_health": avg_health,
            "open_tickets": len(open_tickets),
        },
        "zones": zones_out,
        "alerts": [a.model_dump(mode="json") for a in reversed(store.alerts[-40:])],
        "tickets": [t.model_dump(mode="json") for t in reversed(store.tickets[-30:])],
        "scenarios": [
            {"kind": kind, **{k: v for k, v in sc.items() if k not in ("started_tick",)}}
            for kind, sc in store.scenarios.items()
        ],
        "timeseries": list(store.timeseries),
        "risk_devices": [
            {
                "device_id": d.device_id, "type": d.type, "zone": d.zone,
                "health_score": d.health_score, "risk": d.risk,
                "failure_probability_7d": d.failure_probability,
                "flow_variance_pct": round(d.flow_variance_pct, 1),
                "anomaly_frequency": d.anomaly_frequency,
                "flush_irregularity": d.flush_irregularity,
                "sensor_errors": d.sensor_errors,
            }
            for d in sorted(high_risk + [x for x in store.devices.values() if x.risk == "MEDIUM"],
                            key=lambda x: x.health_score)[:12]
        ],
    }


def _append_timeseries(store: Store) -> None:
    total_flow = round(sum(d.flow_lpm for d in store.devices.values()), 2)
    open_count = sum(1 for a in store.alerts if a.status == "OPEN")
    store.timeseries.append({
        "t": utcnow().isoformat(),
        "flow": total_flow,
        "alerts": open_count,
        "sim_min": store.tick_count,
    })
