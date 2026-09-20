"""KOHLER AquaGuard AI — Predictive Asset Lifecycle & Degradation Engine.

Tracks cumulative mechanical cycle wear, acoustic/vibration cavitation degradation,
and models 7-day predictive failure trajectories before physical leak manifestation.
"""

from typing import Any, Dict, List
import math
from datetime import datetime, timezone

# Rated Lifespan Cycles per Fixture Category
RATED_LIFECYCLE_CYCLES = {
    "flush_valve": 500_000,
    "urinal": 750_000,
    "faucet": 1_000_000,
}


def calculate_fixture_lifecycle(dev, tick_count: int = 0) -> Dict[str, Any]:
    """Computes cycle wear, acoustic/vibration vibration index, and 7-day degradation forecast."""
    dev_type = getattr(dev, "type", "flush_valve")
    rated_cycles = RATED_LIFECYCLE_CYCLES.get(dev_type, 500_000)

    # Base cycles on fixture ID seed + tick usage for deterministic realistic behavior
    seed = abs(hash(dev.device_id)) % 250_000
    cycles_estimated = seed + (getattr(dev, "flush_count", 0) * 150) + (tick_count * 2)
    cycles_used = min(rated_cycles, cycles_estimated)
    cycle_wear_pct = round((cycles_used / rated_cycles) * 100.0, 1)

    # Vibration / acoustic chatter index (0 = quiet, 100 = severe water hammer)
    flow = getattr(dev, "flow_lpm", 0.0)
    health = getattr(dev, "health_score", 90)
    base_chatter = (100 - health) * 0.7
    vibration_index = min(100.0, round(base_chatter + (15.0 if flow > 2.0 else 2.0), 1))

    # Wear velocity (points of health degradation expected per 1000 operational cycles)
    wear_velocity = round(0.4 + (0.8 if cycle_wear_pct > 70 else 0.2) + (0.5 if dev.risk == "HIGH" else 0.1), 2)

    # 7-Day Predicted Health Trajectory
    trajectory_7d = []
    curr_h = float(health)
    for day in range(8):
        drop = day * wear_velocity * (1.5 if dev.risk == "HIGH" else 0.8)
        pred_h = max(10, round(curr_h - drop, 1))
        trajectory_7d.append({
            "day": day,
            "projected_health": pred_h,
            "failure_risk_pct": min(99, round(max(0, (75 - pred_h) * 1.8), 1))
        })

    # Preventive Action
    if cycle_wear_pct >= 85 or health < 50:
        action = "Schedule Proactive Overhaul (Next Maintenance Window)"
        status = "CRITICAL_MAINTENANCE"
    elif cycle_wear_pct >= 70 or health < 70:
        action = "Inspect Seal & Replace Diaphragm Cartridge"
        status = "PREDICTIVE_WATCH"
    else:
        action = "Nominal Operation — Next Regular Service in 90 Days"
        status = "OPTIMAL"

    return {
        "device_id": dev.device_id,
        "type": dev_type,
        "zone": dev.zone,
        "terminal": getattr(dev, "terminal", "Terminal 2"),
        "current_health": health,
        "cycles_completed": cycles_used,
        "rated_cycles": rated_cycles,
        "cycle_wear_pct": cycle_wear_pct,
        "vibration_chatter_index": vibration_index,
        "wear_velocity_pts_per_kcycle": wear_velocity,
        "failure_probability_7d": getattr(dev, "failure_probability", 0.05),
        "status": status,
        "recommended_action": action,
        "trajectory_7d": trajectory_7d,
    }


def get_fleet_lifecycle(store) -> List[Dict[str, Any]]:
    """Returns degradation lifecycle analysis across all fixtures."""
    return [
        calculate_fixture_lifecycle(dev, store.tick_count)
        for dev in store.devices.values()
    ]


def get_predictive_overview(store) -> Dict[str, Any]:
    """Aggregates fleet lifecycle health into high-level predictive maintenance KPIs."""
    fleet = get_fleet_lifecycle(store)
    critical_replacements = [f for f in fleet if f["status"] == "CRITICAL_MAINTENANCE"]
    watch_list = [f for f in fleet if f["status"] == "PREDICTIVE_WATCH"]

    avg_wear = round(sum(f["cycle_wear_pct"] for f in fleet) / max(len(fleet), 1), 1)
    avg_vibration = round(sum(f["vibration_chatter_index"] for f in fleet) / max(len(fleet), 1), 1)

    # Top 5 most vulnerable fixtures requiring proactive maintenance
    vulnerable_assets = sorted(fleet, key=lambda x: (x["trajectory_7d"][-1]["failure_risk_pct"]), reverse=True)[:5]

    return {
        "total_monitored_assets": len(fleet),
        "assets_requiring_overhaul": len(critical_replacements),
        "assets_on_predictive_watch": len(watch_list),
        "average_fleet_wear_pct": avg_wear,
        "average_vibration_index": avg_vibration,
        "proactive_cost_savings_inr": len(critical_replacements) * 14500.0, # Avoided water loss + emergency labor
        "top_vulnerable_assets": vulnerable_assets,
    }
