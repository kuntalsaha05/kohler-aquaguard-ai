"""Sensor Fusion, Diagnostic Discrimination, & Adaptive Baseline Engine."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    np = None


def get_contextual_baseline_flow(zone_name: str, terminal: str, hour: int) -> float:
    """Context-aware nominal flow baseline f(hour, terminal, location).

    Accounts for Pune Airport flight bank schedules:
    - 00:00 - 04:30: Red-eye low lull (0.05 L/min expected idle)
    - 05:00 - 09:30: Morning departure peak (1.8 L/min expected nominal)
    - 10:00 - 16:30: Daytime steady state (0.9 L/min)
    - 17:00 - 22:30: Evening rush bank (1.6 L/min)
    """
    if 0 <= hour < 5:
        mult = 0.15
    elif 5 <= hour < 10:
        mult = 1.4
    elif 10 <= hour < 17:
        mult = 0.85
    elif 17 <= hour < 22:
        mult = 1.25
    else:
        mult = 0.5

    terminal_weight = 1.2 if "Terminal 2" in terminal else (1.0 if "Terminal 1" in terminal else 0.9)
    return round(0.85 * mult * terminal_weight, 2)


def evaluate_sensor_diagnostics(
    flow_lpm: float,
    occupancy: int,
    flush_count: int,
    sensor_errors: int,
    battery_pct: float,
    history_window: List[dict],
) -> Dict[str, Any]:
    """Diagnose individual sensor reliability & compute overall telemetry confidence."""
    # 1. Flow sensor confidence
    flow_conf = 0.98
    if sensor_errors > 0:
        flow_conf -= min(0.40, sensor_errors * 0.08)
    if battery_pct < 20.0:
        flow_conf -= 0.15

    # 2. Occupancy sensor confidence
    occ_conf = 0.95
    if battery_pct < 15.0:
        occ_conf -= 0.20

    # 3. Flush sensor confidence
    flush_conf = 0.99
    if sensor_errors > 2:
        flush_conf -= 0.15

    # Overall weighted telemetry confidence
    overall = round(0.45 * flow_conf + 0.35 * occ_conf + 0.20 * flush_conf, 2)
    overall = max(0.20, min(0.99, overall))

    # Fault discrimination: Physical leak vs Broken sensor node
    is_sensor_malfunction = (sensor_errors >= 3 and flow_conf < 0.70) or (battery_pct < 10.0 and flow_lpm > 0.5)

    return {
        "flow_sensor_confidence": round(flow_conf, 2),
        "occupancy_sensor_confidence": round(occ_conf, 2),
        "flush_sensor_confidence": round(flush_conf, 2),
        "overall_telemetry_confidence": overall,
        "is_sensor_malfunction": is_sensor_malfunction,
        "discrimination": "SENSOR_MALFUNCTION" if is_sensor_malfunction else "PHYSICAL_WATER_FAULT",
    }


def compute_sensor_fusion_confidence(
    flow_lpm: float,
    expected_baseline_lpm: float,
    occupancy: int,
    flush_count: int,
    duration_min: int,
    flow_variance_pct: float,
    pressure_bar: float,
    sensor_confidence: float,
    history_flows: List[float],
) -> Dict[str, Any]:
    """Multi-sensor fusion calculation for leak & incident confidence.

    Formula:
    Leak Confidence =
        0.30 * Flow Anomaly
      + 0.20 * Occupancy Mismatch
      + 0.15 * Flush Mismatch
      + 0.15 * Historical Baseline Deviation
      + 0.10 * Pressure Anomaly
      + 0.10 * Sensor Diagnostic Confidence
    """
    # 1. Flow anomaly (0 to 1)
    flow_anom = min(1.0, max(0.0, (flow_lpm - 0.2) / 2.5)) if flow_lpm > 0.2 else 0.0

    # 2. Occupancy mismatch (Flow occurs without occupancy)
    occ_mismatch = 1.0 if (flow_lpm > 0.3 and occupancy == 0) else (0.2 if occupancy == 0 else 0.0)

    # 3. Flush mismatch (Flow without flush command)
    flush_mismatch = 1.0 if (flow_lpm > 0.3 and flush_count == 0) else 0.0

    # 4. Historical baseline deviation
    if expected_baseline_lpm > 0:
        ratio = flow_lpm / expected_baseline_lpm
        hist_dev = min(1.0, max(0.0, (ratio - 1.0) / 3.0)) if ratio > 1.0 else 0.0
    else:
        hist_dev = 1.0 if flow_lpm > 0.5 else 0.0

    # 5. Pressure anomaly (pressure drops under 2.0 bar with elevated flow)
    press_anom = min(1.0, max(0.0, (2.2 - pressure_bar) / 1.2)) if pressure_bar < 2.2 else 0.0

    # Weighted Sensor Fusion Sum
    leak_conf = (
        0.30 * flow_anom +
        0.20 * occ_mismatch +
        0.15 * flush_mismatch +
        0.15 * hist_dev +
        0.10 * press_anom +
        0.10 * sensor_confidence
    )

    leak_confidence_pct = int(round(min(0.99, max(0.05, leak_conf)) * 100))

    # Root Cause Classification
    if press_anom > 0.5 and flow_lpm > 2.0:
        root_cause = "Supply-Line Fracture / Main Riser Drop"
        root_cause_conf = 0.89
    elif flush_count > 1 and occupancy == 0:
        root_cause = "Solenoid Valve Auto-Cycle Leakage"
        root_cause_conf = 0.92
    elif flow_lpm > 1.5 and occupancy == 0 and flush_count == 0:
        root_cause = "Flush Valve Diaphragm Tear"
        root_cause_conf = 0.96
    elif flow_variance_pct > 30.0:
        root_cause = "Inlet Seal Mechanical Wear"
        root_cause_conf = 0.81
    elif occupancy > 5 and flow_lpm > 1.0:
        root_cause = "Abnormal Passenger Volume Surge"
        root_cause_conf = 0.84
    else:
        root_cause = "Telemetry Drift / Nominal"
        root_cause_conf = 0.70

    return {
        "leak_confidence_pct": leak_confidence_pct,
        "root_cause": root_cause,
        "root_cause_confidence": root_cause_conf,
        "components": {
            "flow_anomaly_contrib": round(flow_anom * 30, 1),
            "occupancy_mismatch_contrib": round(occ_mismatch * 20, 1),
            "flush_mismatch_contrib": round(flush_mismatch * 15, 1),
            "historical_deviation_contrib": round(hist_dev * 15, 1),
            "pressure_anomaly_contrib": round(press_anom * 10, 1),
            "sensor_confidence_contrib": round(sensor_confidence * 10, 1),
        },
    }
