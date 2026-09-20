"""Machine Learning & Anomaly Scoring Engine for KOHLER AquaGuard AI."""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List

try:
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    np = None


def compute_anomaly_score(
    flow_lpm: float,
    expected_flow_lpm: float,
    occupancy: int,
    flush_count: int,
    duration_min: int,
    sensor_errors: int,
    flow_variance_pct: float = 0.0,
    pressure_bar: float = 3.0,
) -> Dict[str, Any]:
    """Composite 0–100 Anomaly Score: NORMAL (0-30), WATCH (30-60), ANOMALOUS (60-80), CRITICAL (80-100)."""
    score = 0.0
    factors = []

    # 1. Unoccupied continuous flow
    if flow_lpm > 0.3 and occupancy == 0 and flush_count == 0:
        pts = min(45.0, 20.0 + (flow_lpm * 7.5) + min(15.0, duration_min * 1.5))
        score += pts
        factors.append(f"Unoccupied flow ({flow_lpm:.1f} L/min for {duration_min}m)")

    # 2. Ghost / phantom flushes
    if flush_count > 0 and occupancy == 0:
        pts = min(35.0, flush_count * 12.0)
        score += pts
        factors.append(f"Phantom flush pattern ({flush_count} flushes with 0 occupancy)")

    # 3. Flow instability
    if flow_variance_pct > 25.0:
        pts = min(20.0, (flow_variance_pct - 25.0) * 0.5)
        score += pts
        factors.append(f"Flow variance ({flow_variance_pct:.1f}%)")

    # 4. Sensor telemetry dropouts
    if sensor_errors > 0:
        pts = min(25.0, sensor_errors * 6.0)
        score += pts
        factors.append(f"Sensor error pulses ({sensor_errors})")

    # 5. Supply pressure drops
    if pressure_bar < 2.0 and flow_lpm > 0.5:
        pts = min(25.0, (2.0 - pressure_bar) * 25.0)
        score += pts
        factors.append(f"Low line pressure ({pressure_bar:.1f} bar)")

    final_score = int(min(100.0, round(score)))
    band = "CRITICAL" if final_score >= 80 else ("ANOMALOUS" if final_score >= 60 else ("WATCH" if final_score >= 30 else "NORMAL"))

    return {
        "score": final_score,
        "band": band,
        "factors": factors or ["Nominal telemetry"],
    }


class FailureRiskModel:
    """7-Day failure risk model trained on simulated fixture telemetry."""

    def __init__(self):
        self.model = None
        self._fit_baseline()

    def _fit_baseline(self):
        if not SKLEARN_AVAILABLE or np is None:
            return
        rng = np.random.RandomState(42)
        n = 1500
        # Features: [idle_flow, variance, irregularity, errors, cycles/1000]
        X = np.zeros((n, 5))
        # Healthy fixtures
        X[:1100, 0] = rng.exponential(0.04, 1100)
        X[:1100, 1] = rng.normal(8.0, 3.0, 1100).clip(0, 25)
        X[:1100, 2] = rng.poisson(0.2, 1100)
        X[:1100, 3] = rng.poisson(0.1, 1100)
        X[:1100, 4] = rng.uniform(1.0, 15.0, 1100)
        y = np.zeros(n)

        # Degrading fixtures
        X[1100:, 0] = rng.normal(1.2, 0.5, 400).clip(0.1, 3.5)
        X[1100:, 1] = rng.normal(38.0, 12.0, 400).clip(15, 80)
        X[1100:, 2] = rng.poisson(3.2, 400)
        X[1100:, 3] = rng.poisson(2.5, 400)
        X[1100:, 4] = rng.uniform(22.0, 45.0, 400)
        y[1100:] = 1

        self.model = RandomForestClassifier(n_estimators=40, max_depth=5, random_state=42)
        self.model.fit(X, y)

    def predict(self, dev_state: Any) -> Dict[str, Any]:
        idle = getattr(dev_state, "idle_flow_mean", 0.0)
        var_pct = getattr(dev_state, "flow_variance_pct", 5.0)
        irreg = getattr(dev_state, "flush_irregularity", 0)
        errs = getattr(dev_state, "sensor_errors", 0)
        cycles = getattr(dev_state, "cumulative_cycles", 5200) / 1000.0

        if SKLEARN_AVAILABLE and self.model and np is not None:
            x = np.array([[idle, var_pct, irreg, errs, cycles]])
            prob = float(self.model.predict_proba(x)[0][1])
        else:
            raw = (idle * 0.38 + (var_pct / 50.0) * 0.25 + irreg * 0.15 + errs * 0.15 + (cycles / 40.0) * 0.07)
            prob = min(0.96, max(0.02, raw))

        # Attributed feature importance factors
        weights = [
            ("Idle flow frequency", idle * 15.0),
            ("Flow variance", var_pct * 0.6),
            ("Flush irregularity", irreg * 16.0),
            ("Sensor errors", errs * 18.0),
            ("Cycle fatigue", (cycles / 35.0) * 15.0),
        ]
        weights.sort(key=lambda item: item[1], reverse=True)
        top_factors = [w[0] for w in weights[:3] if w[1] > 2.0]

        return {
            "failure_probability_7d": round(prob, 2),
            "risk": "HIGH" if prob >= 0.65 else ("MEDIUM" if prob >= 0.30 else "LOW"),
            "contributing_factors": top_factors or ["Operating within normal tolerance"],
        }


FAILURE_MODEL = FailureRiskModel()
