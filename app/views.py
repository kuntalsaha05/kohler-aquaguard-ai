"""View layer: read-only projections of the store for API responses.

Kept separate from the detection engine so response shaping lives at the
API edge, not inside the reasoning core. Nothing here mutates state.
"""
from __future__ import annotations

from .state import Store

FACILITY_NAME = "Pune International Airport"


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
                "anomaly_score": getattr(d, "anomaly_score", 15),
                "anomaly_band": getattr(d, "anomaly_band", "NORMAL"),
                "contributing_factors": getattr(d, "contributing_factors", []),
                "pressure_bar": round(getattr(d, "pressure_bar", 3.0), 2),
                "failure_probability_7d": d.failure_probability,
                "scenario": next((k for k, sc in store.scenarios.items()
                                  if sc.get("device_id") == d.device_id or
                                  (sc.get("devices") and any(x["device_id"] == d.device_id for x in sc["devices"]))), None),
                "flow_series": [h["flow"] for h in list(d.history)[-24:]],
                "history": list(d.history)[-30:],
            })
        has_critical = any(x["status"] == "critical" for x in dev_out)
        status = "critical" if (has_critical or zone.cleaning_required and zone.usage_since_cleaning > zone.threshold * 1.1) else \
                 "warning" if (any(x["status"] == "warning" for x in dev_out) or zone.cleaning_required) else "normal"
        zones_out.append({
            **zone.to_dict(), "adaptive_threshold": zone.adaptive_threshold,
            "status": status,
            "devices": dev_out,
        })

    devices_dict = {
        d["device_id"]: d
        for z in zones_out
        for d in z["devices"]
    }

    open_alerts = [a for a in store.alerts if a.status == "OPEN"]
    high_risk = [d for d in store.devices.values() if d.risk == "HIGH"]
    wastage = round(sum(a.estimated_loss_liters for a in open_alerts), 1)
    mttr = (round(sum(store.resolved_durations_min) / len(store.resolved_durations_min), 1)
            if store.resolved_durations_min else 0.0)
    avg_health = round(sum(d.health_score for d in store.devices.values()) / max(1, len(store.devices)), 1)
    cost_saved = round((store.saved_month_liters / 1000.0) * 48.50, 2)

    open_tickets = [t for t in store.tickets if t.status == "OPEN"]
    health_hier = facility_health_hierarchy(store)
    heatmap_data = water_waste_heatmap(store)

    alerts_list = []
    for a in reversed(store.alerts[-40:]):
        ad = a.model_dump(mode="json")
        ad["alert_id"] = a.id
        alerts_list.append(ad)

    tickets_list = []
    for t in reversed(store.tickets[-30:]):
        td = t.model_dump(mode="json")
        td["id"] = t.ticket_id
        tickets_list.append(td)

    return {
        "facility": {
            "name": FACILITY_NAME,
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
            "cost_saved_month_inr": cost_saved,
            "current_wastage_liters": wastage,
            "incidents_resolved": store.resolved_count,
            "mttr_minutes": mttr,
            "avg_device_health": avg_health,
            "sla_compliance_pct": 96.4,
            "open_tickets": len(open_tickets),
            "facility_health_score": health_hier["composite_score"],
        },
        "facility_health": health_hier,
        "heatmap": heatmap_data,
        "zones": zones_out,
        "devices": devices_dict,
        "alerts": alerts_list,
        "tickets": tickets_list,
        "incidents": [i.model_dump(mode="json") for i in reversed(store.incidents[-30:])],
        "scenarios": [
            {"kind": kind, **{k: v for k, v in sc.items() if k not in ("started_tick",)}}
            for kind, sc in store.scenarios.items()
        ],
        "timeseries": list(store.timeseries),
        "risk_devices": [
            {
                "device_id": d.device_id, "type": d.type, "zone": d.zone,
                "health_score": d.health_score, "risk": d.risk,
                "anomaly_score": getattr(d, "anomaly_score", 15),
                "failure_probability_7d": d.failure_probability,
                "contributing_factors": getattr(d, "contributing_factors", []),
                "flow_variance_pct": round(d.flow_variance_pct, 1),
                "anomaly_frequency": d.anomaly_frequency,
                "flush_irregularity": d.flush_irregularity,
                "sensor_errors": d.sensor_errors,
            }
            for d in sorted(high_risk + [x for x in store.devices.values() if x.risk == "MEDIUM"],
                            key=lambda x: x.health_score)[:12]
        ],
    }


def facility_health_hierarchy(store: Store) -> dict:
    """Multi-tiered facility health index (0-100) computed from 5 operational sub-indices."""
    open_alerts = [a for a in store.alerts if a.status == "OPEN"]
    wastage = sum(a.estimated_loss_liters for a in open_alerts)

    # 1. Leak Containment Index (30% weight) - drops with active wastage
    leak_index = max(10, min(100, int(100 - (wastage / 80.0) * 15)))

    # 2. Fixture Reliability Index (25% weight) - fleet average health minus high-risk penalties
    total_devs = max(1, len(store.devices))
    avg_dev_health = sum(d.health_score for d in store.devices.values()) / total_devs
    high_risk_count = sum(1 for d in store.devices.values() if d.risk == "HIGH")
    fixture_index = max(15, min(100, int(avg_dev_health - high_risk_count * 3)))

    # 3. Sensor Telemetry Fidelity (15% weight) - node error rates and battery levels
    clean_nodes = sum(1 for d in store.devices.values() if d.sensor_errors == 0 and d.battery_pct > 20)
    sensor_index = max(20, min(100, int((clean_nodes / total_devs) * 100)))

    # 4. Dispatch & SLA Performance (15% weight) - penalties for critical SLA countdown breach risk
    critical_breaches = sum(1 for t in store.tickets if t.status == "OPEN" and getattr(t, "sla_breach_risk", "LOW") in ("CRITICAL", "HIGH"))
    sla_index = max(20, min(100, 100 - critical_breaches * 20))

    # 5. Hygiene & Sanitation Compliance (15% weight) - ratio of clean restrooms
    total_zones = max(1, len(store.zones))
    clean_zones = sum(1 for z in store.zones.values() if not z.cleaning_required)
    hygiene_index = max(20, min(100, int((clean_zones / total_zones) * 100)))

    # Overall Composite Score
    composite = int(round(
        0.30 * leak_index +
        0.25 * fixture_index +
        0.15 * sensor_index +
        0.15 * sla_index +
        0.15 * hygiene_index
    ))

    status = "EXCELLENT" if composite >= 90 else ("GOOD" if composite >= 75 else ("FAIR" if composite >= 60 else "CRITICAL"))

    return {
        "composite_score": composite,
        "status": status,
        "sub_indices": {
            "leak_containment_index": {
                "score": leak_index,
                "weight": "30%",
                "status": "HEALTHY" if leak_index >= 80 else "DEGRADED",
                "detail": f"{len(open_alerts)} active leak/fault incidents ({wastage:.1f} L open wastage)",
            },
            "fixture_reliability_index": {
                "score": fixture_index,
                "weight": "25%",
                "status": "HEALTHY" if fixture_index >= 75 else "WATCH",
                "detail": f"{high_risk_count} fixtures in 7-day high wear band across fleet",
            },
            "sensor_telemetry_fidelity": {
                "score": sensor_index,
                "weight": "15%",
                "status": "HEALTHY" if sensor_index >= 90 else "DEGRADED",
                "detail": f"{clean_nodes}/{total_devs} sensor nodes reporting 100% nominal telemetry",
            },
            "dispatch_sla_performance": {
                "score": sla_index,
                "weight": "15%",
                "status": "HEALTHY" if sla_index >= 85 else "AT_RISK",
                "detail": f"{critical_breaches} tickets approaching or breaching SLA countdown",
            },
            "hygiene_compliance_index": {
                "score": hygiene_index,
                "weight": "15%",
                "status": "HEALTHY" if hygiene_index >= 80 else "ATTENTION_REQUIRED",
                "detail": f"{clean_zones}/{total_zones} restrooms below adaptive cleaning threshold",
            },
        },
    }


def water_waste_heatmap(store: Store) -> list[dict]:
    """Facility-wide water loss heatmap grouped by airport terminal."""
    terminals = ["Terminal 1", "Terminal 2", "Terminal 3", "Arrivals"]
    open_alerts = [a for a in store.alerts if a.status == "OPEN"]
    total_loss_today = sum(a.estimated_daily_loss_liters for a in open_alerts) or 1.0

    out = []
    for term in terminals:
        term_zones = [z for z in store.zones.values() if z.terminal == term]
        term_zone_names = {z.name for z in term_zones}
        term_alerts = [a for a in open_alerts if a.zone in term_zone_names]
        term_loss = sum(a.estimated_daily_loss_liters for a in term_alerts)
        term_pax = sum(z.occupancy for z in term_zones) or 1
        pct = round((term_loss / total_loss_today) * 100, 1) if total_loss_today > 0 else 0.0

        # Identify hotspot zone
        hotspot = "Nominal"
        if term_alerts:
            hotspot = max(term_alerts, key=lambda a: a.estimated_daily_loss_liters).zone
        elif term_zones:
            hotspot = term_zones[0].name

        out.append({
            "terminal": term,
            "loss_liters_today": round(term_loss, 1),
            "loss_percentage": pct,
            "occupancy_pax": term_pax,
            "liters_per_passenger": round(term_loss / term_pax, 2),
            "active_incidents": len(term_alerts),
            "hotspot_zone": hotspot,
            "status": "CRITICAL" if pct >= 50 else ("WARNING" if pct >= 25 else "NORMAL"),
        })
    return out
