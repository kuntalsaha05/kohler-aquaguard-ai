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
                "scenario": next((k for k, sc in store.scenarios.items()
                                  if sc.get("device_id") == d.device_id), None),
                "flow_series": [h["flow"] for h in list(d.history)[-24:]],
            })
        has_critical = any(x["status"] == "critical" for x in dev_out)
        status = "critical" if (has_critical or zone.cleaning_required and zone.usage_since_cleaning > zone.threshold * 1.1) else \
                 "warning" if (any(x["status"] == "warning" for x in dev_out) or zone.cleaning_required) else "normal"
        zones_out.append({
            **zone.to_dict(), "adaptive_threshold": zone.adaptive_threshold,
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
