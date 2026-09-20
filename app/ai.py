"""AI explanation layer.

All numbers are produced by the deterministic engine (engine.py) — this module
only turns computed facts into clear operational language, per the design rule
"the reasoning layer explains; it never invents data".

The composer is deterministic so the demo works with zero external
dependencies; it can be swapped for an LLM call that receives the same
structured `facts` dict.
"""
from __future__ import annotations

from typing import Any, Dict

from .state import HOUSEHOLD_DAY_LITERS, LITERS_PER_FLUSH, Store


def _fmt(n: float) -> str:
    return f"{n:,.0f}" if n >= 100 else f"{n:,.1f}"


# ------------------------------------------------------------- diagnosis

def compose_diagnosis(kind: str, facts: Dict[str, Any]) -> Dict[str, str]:
    if kind == "continuous_leak":
        flow = facts.get("flow_lpm", 0.0)
        dur = facts.get("duration_min", facts.get("episode_min", 0))
        daily = facts.get("daily_loss") or flow * 1440
        monthly = facts.get("monthly_loss") or daily * 30
        loss_so_far = facts.get("loss_so_far") or flow * dur
        diagnosis = (
            f"{facts['device_id']} ({facts['device_type']}, {facts['zone']}) shows continuous flow of "
            f"{flow:.1f} L/min for {dur} minutes despite zero detected occupancy and no flush events. "
            f"This pattern is inconsistent with normal usage and points to a failed valve seal or "
            f"flush mechanism stuck in the open position. Current loss is estimated at "
            f"{_fmt(loss_so_far)} L so far, {_fmt(daily)} L/day and "
            f"{_fmt(monthly)} L/month if left unresolved."
        )
        action = "Dispatch plumbing maintenance immediately; isolate water supply to this fixture."
        return {"diagnosis": diagnosis, "recommended_action": action}

    if kind == "phantom_flush":
        events = facts.get("flush_events_zero_occupancy", facts.get("flush_count", 0))
        rate = facts.get("estimated_flush_rate_per_min", 0.0)
        daily = facts.get("daily_loss") or rate * LITERS_PER_FLUSH * 1440
        diagnosis = (
            f"{facts['device_id']} ({facts['device_type']}, {facts['zone']}) registered "
            f"{events} flush events with zero occupancy in the observation window "
            f"(~{rate:.1f} flushes/min). Actuation without users indicates a faulty solenoid or "
            f"mis-calibrated flush sensor. Wasted water is estimated at {_fmt(daily)} L/day "
            f"at {rate:.1f} flushes/min × 6 L per flush."
        )
        action = "Dispatch plumbing to inspect the solenoid valve and recalibrate the flush sensor."
        return {"diagnosis": diagnosis, "recommended_action": action}

    if kind == "sensor_fault":
        errors = facts.get("sensor_error_ticks", facts.get("sensor_errors", 0))
        diagnosis = (
            f"{facts['device_id']} ({facts['device_type']}, {facts['zone']}) returned flatlined "
            f"readings with {errors} sensor-error ticks and battery at "
            f"{facts.get('battery_pct', 100):.0f}%. Frozen telemetry hides real usage and can mask "
            f"leaks in this zone, so the device itself is now an operational risk."
        )
        action = "Dispatch instrumentation team to replace the sensor node and verify calibration."
        return {"diagnosis": diagnosis, "recommended_action": action}

    if kind == "predictive":
        diagnosis = (
            f"Health model for {facts['device_id']} ({facts['device_type']}, {facts['zone']}) "
            f"projects a {facts.get('failure_probability', 0):.0%} probability of failure within 7 days. "
            f"Drivers: health score {facts.get('health_score', '?')}/100, flow variance "
            f"{facts.get('flow_variance_pct', 0):.0f}% above baseline, idle flow "
            f"{facts.get('idle_flow_lpm', 0):.2f} L/min, {facts.get('sensor_errors', 0)} sensor errors. "
            f"Replace or service the unit before failure to avoid an unplanned outage."
        )
        action = "Schedule preventive inspection within 72 hours; check seals and actuator wear."
        return {"diagnosis": diagnosis, "recommended_action": action}

    if kind == "hygiene":
        diagnosis = (
            f"{facts['zone']} has recorded {facts.get('usage', 0)} interactions since last cleaning, "
            f"exceeding its adaptive hygiene threshold of {facts.get('threshold', 900)} "
            f"(+{facts.get('over_pct', 0):.0f}% over target) with {facts.get('occupancy', 0)} people "
            f"currently inside and last cleaning {facts.get('last_cleaned_min_ago', 0)} minutes ago. "
            f"Traffic pressure puts this restroom below the facility hygiene standard."
        )
        action = "Dispatch housekeeping crew for immediate cleaning; restock consumables."
        return {"diagnosis": diagnosis, "recommended_action": action}

    diagnosis = (f"{facts.get('device_id', 'Device')} in {facts.get('zone', 'unknown zone')} shows "
                 f"anomalous telemetry; inspect flow control and sensor health.")
    return {"diagnosis": diagnosis, "recommended_action": "Inspect the fixture."}


def compose_ticket_summary(alert) -> str:
    loss = alert.estimated_daily_loss_liters
    loss_txt = f" Est. water loss {_fmt(loss)} L/day." if loss > 0 else ""
    return (f"Auto-generated from {alert.id} ({alert.kind.replace('_', ' ')}). "
            f"Severity {alert.severity}, priority {alert.priority}.{loss_txt} "
            f"{alert.recommended_action}")


def compose_resolution_note(alert, store: Store) -> str:
    if alert.kind in ("continuous_leak", "phantom_flush"):
        monthly = alert.estimated_monthly_loss_liters
        household_days = monthly / HOUSEHOLD_DAY_LITERS
        return (
            f"Resolution verified: telemetry for {alert.device_id} returned to baseline "
            f"(no idle flow, no unexplained flushes). Estimated {_fmt(monthly)} L/month of "
            f"loss avoided — equivalent to about {_fmt(household_days)} days of household "
            f"water use. Logged to the sustainability ledger."
        )
    if alert.kind == "hygiene":
        return f"Cleaning completed for {alert.zone}; hygiene counter reset and threshold monitoring continues."
    if alert.kind == "predictive":
        return f"Preventive inspection scheduled/completed for {alert.device_id}; risk model reset after service."
    return f"Incident {alert.id} resolved and verified against telemetry."


# ------------------------------------------------------- command center

def _open_alerts(store: Store):
    return [a for a in store.alerts if a.status == "OPEN"]


def _sorted_by_loss(store: Store):
    return sorted(_open_alerts(store), key=lambda a: a.estimated_daily_loss_liters, reverse=True)


def command_center_answer(store: Store, query: str) -> str:
    q = query.lower().strip()
    alerts = _sorted_by_loss(store)

    if any(w in q for w in ("wast", "losing water", "where is water")):
        if not alerts:
            return ("No abnormal water consumption detected right now. Facility flow is within "
                    "expected ranges across all zones.")
        total_daily = sum(a.estimated_daily_loss_liters for a in alerts)
        top = alerts[0]
        share = (top.estimated_daily_loss_liters / total_daily * 100) if total_daily else 0
        others = [a for a in alerts[1:4] if a.estimated_daily_loss_liters > 0]
        extra = " ".join(
            f"Next: {a.device_id} in {a.zone} at {_fmt(a.estimated_daily_loss_liters)} L/day;"
            for a in others
        )
        return (f"Active incidents are wasting an estimated {_fmt(total_daily)} L/day. "
                f"{top.device_id} in {top.zone} accounts for {share:.0f}% of it "
                f"({_fmt(top.estimated_daily_loss_liters)} L/day, {top.severity}). {extra} "
                f"Resolving the top incident saves ~{_fmt(top.estimated_monthly_loss_liters)} L/month.")

    if any(w in q for w in ("fix first", "priority", "prioritize", "should i", "first?", "do first")):
        if not alerts:
            return ("Nothing needs attention — no open incidents. Predictive monitoring continues "
                    "on all devices.")
        ranked = [a for a in alerts if a.kind in ("continuous_leak", "phantom_flush")] + \
                 [a for a in alerts if a.kind == "predictive"] + \
                 [a for a in alerts if a.kind in ("sensor_fault", "hygiene")]
        lines = []
        for i, a in enumerate(ranked[:3], 1):
            sla = {"P1": "immediately", "P2": "within 4 hours", "P3": "within 24 hours"}.get(a.priority, "soon")
            lines.append(f"{i}. {a.device_id} in {a.zone} — {a.issue} ({a.severity}, {a.priority}; dispatch {sla})")
        return (f"{len(ranked)} open incident(s), ranked by impact: " + " ".join(lines) +
                f" Recommended first action: {ranked[0].recommended_action}")

    if any(w in q for w in ("hygiene", "clean", "housekeep")):
        dirty = [z for z in store.zones.values() if z.cleaning_required]
        near = sorted(store.zones.values(),
                      key=lambda z: z.usage_since_cleaning / max(1, z.threshold), reverse=True)
        if dirty:
            parts = ", ".join(f"{z.name} ({z.usage_since_cleaning}/{z.threshold} interactions)" for z in dirty)
            return f"{len(dirty)} restroom(s) need cleaning now: {parts}. Housekeeping tickets were auto-generated."
        worst = near[0] if near else None
        if worst:
            pct = worst.usage_since_cleaning / max(1, worst.threshold) * 100
            return (f"No zone has breached its hygiene threshold yet. Closest: {worst.name} at "
                    f"{pct:.0f}% of threshold ({worst.usage_since_cleaning}/{worst.threshold} interactions).")
        return "Hygiene status is healthy across the facility."

    if any(w in q for w in ("risk", "predict", "fail", "health", "degrad")):
        risky = sorted([d for d in store.devices.values() if d.risk != "LOW"],
                       key=lambda d: d.health_score)
        if not risky:
            avg = sum(d.health_score for d in store.devices.values()) / max(1, len(store.devices))
            return (f"All devices are rated LOW risk (average health {avg:.0f}/100). "
                    f"Predictive monitoring continues.")
        top = risky[0]
        return (f"{len(risky)} device(s) flagged at elevated risk. Highest: {top.device_id} "
                f"({top.type}, {top.zone}) — health {top.health_score}/100, "
                f"{top.failure_probability:.0%} failure probability within 7 days. "
                f"Predictive tickets are auto-generated for HIGH-risk devices.")

    if any(w in q for w in ("save", "sustain", "saving", "impact", "conserv")):
        saved = store.saved_month_liters
        household = saved / HOUSEHOLD_DAY_LITERS
        resolved = store.resolved_count
        return (f"Sustainability ledger: {_fmt(saved)} L of monthly loss avoided through "
                f"{resolved} resolved incident(s) — equivalent to ~{_fmt(household)} household-days "
                f"of water (150 L/day). Current open wastage: "
                f"{_fmt(sum(a.estimated_loss_liters for a in _open_alerts(store)))} L and counting.")

    if any(w in q for w in ("status", "overview", "summary", "how are we", "report")):
        open_count = len(_open_alerts(store))
        crit = sum(1 for a in _open_alerts(store) if a.severity in ("HIGH", "CRITICAL"))
        dirty = sum(1 for z in store.zones.values() if z.cleaning_required)
        avg = sum(d.health_score for d in store.devices.values()) / max(1, len(store.devices))
        return (f"Facility status: {len(store.devices)} devices across {len(store.zones)} zones, "
                f"average device health {avg:.0f}/100. {open_count} open incident(s) "
                f"({crit} high/critical), {dirty} zone(s) needing cleaning, "
                f"{_fmt(store.saved_month_liters)} L/month saved so far.")

    if "leak" in q:
        leaks = [a for a in alerts if a.kind in ("continuous_leak", "phantom_flush")]
        if not leaks:
            return "No leaks detected. All fixtures show idle flow at expected levels."
        parts = "; ".join(f"{a.device_id} in {a.zone} ({_fmt(a.estimated_daily_loss_liters)} L/day)" for a in leaks[:4])
        return f"{len(leaks)} leak-type incident(s) active: {parts}."

    if any(w in q for w in ("help", "what can you", "commands")):
        return ("Ask me things like: 'Where are we wasting the most water today?', "
                "'What should I fix first?', 'How is hygiene compliance?', "
                "'Which devices are at risk of failure?', or 'What is our sustainability impact?' "
                "Answers are computed live from facility telemetry.")

    # default: brief + guidance
    open_count = len(_open_alerts(store))
    if open_count:
        top = alerts[0]
        return (f"{open_count} open incident(s); the largest is {top.device_id} in {top.zone} "
                f"({_fmt(top.estimated_daily_loss_liters)} L/day). Try 'What should I fix first?' "
                f"or ask about sustainability, hygiene, or device risk.")
    return ("All systems nominal — no open incidents. Ask 'Which devices are at risk of failure?' "
            "or 'How is hygiene compliance?' for a deeper look.")
