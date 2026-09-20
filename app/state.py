"""Shared models and in-memory state store for AquaGuard AI.

The prototype keeps everything in memory (fast, zero-setup for the hackathon
demo) and persists a JSON snapshot to data/state.json so a server restart
does not wipe the incident story mid-demo.
"""
from __future__ import annotations

import json
import os
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
Risk = Literal["LOW", "MEDIUM", "HIGH"]
Priority = Literal["P1", "P2", "P3", "P4"]

STATE_PATH = os.path.join("data", "state.json")

# Simulation time scale: one telemetry tick represents one simulated minute
# of facility operation, delivered every SIM_INTERVAL_SECONDS of real time.
TICK_MINUTES = 1.0
SIM_INTERVAL_SECONDS = 2.0

LITERS_PER_FLUSH = 6.0
HOUSEHOLD_DAY_LITERS = 150.0


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TelemetryEvent(BaseModel):
    device_id: str
    zone: str
    timestamp: datetime = Field(default_factory=utcnow)
    flow_lpm: float = Field(ge=0)
    occupancy: int = Field(ge=0, default=0)
    flush_count: int = Field(ge=0, default=0)
    expected_flow_lpm: float = Field(ge=0, default=0)
    duration_min: int = Field(ge=0, default=1)
    temperature_c: Optional[float] = None
    sensor_errors: int = Field(ge=0, default=0)
    battery_pct: float = Field(ge=0, le=100, default=100.0)


class Alert(BaseModel):
    id: str
    device_id: str
    device_type: str
    zone: str
    kind: str  # continuous_leak | phantom_flush | sensor_fault | hygiene | predictive
    issue: str
    severity: Severity
    priority: Priority
    estimated_loss_liters: float
    estimated_daily_loss_liters: float
    estimated_monthly_loss_liters: float
    diagnosis: str
    recommended_action: str
    telemetry: Dict[str, Any] = {}
    status: Literal["OPEN", "RESOLVED"] = "OPEN"
    anomaly_score: int = 0
    anomaly_band: str = "NORMAL"
    assigned_technician: Optional[str] = None
    sla_minutes: int = 60
    timeline: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None


class MaintenanceTicket(BaseModel):
    ticket_id: str
    category: str
    asset: str
    location: str
    issue: str
    severity: Severity
    priority: Priority
    estimated_water_loss_daily_liters: float
    action: str
    ai_summary: str
    alert_id: Optional[str] = None
    assigned_technician: Optional[str] = None
    technician_team: Optional[str] = None
    sla_deadline_minutes: int = 60
    eta_minutes: int = 15
    dispatch_rationale: Optional[str] = None
    timeline: List[Dict[str, Any]] = []
    status: Literal["OPEN", "RESOLVED"] = "OPEN"
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: Optional[datetime] = None


class DeviceState:
    """Mutable runtime state for one instrumented fixture."""

    def __init__(self, device_id: str, dtype: str, zone_id: str, zone: str,
                 terminal: str, floor: int, expected_flow_lpm: float = 0.0):
        self.device_id = device_id
        self.type = dtype
        self.zone_id = zone_id
        self.zone = zone
        self.terminal = terminal
        self.floor = floor
        self.expected_flow_lpm = expected_flow_lpm
        # live telemetry
        self.flow_lpm = 0.0
        self.occupancy = 0
        self.flush_count = 0
        self.duration_min = 1
        self.sensor_errors = 0
        self.battery_pct = 100.0
        self.episode_min = 0  # consecutive minutes of abnormal flow
        # rolling window used by the health model
        self.history: deque = deque(maxlen=40)
        self.health_score = 100
        self.risk: Risk = "LOW"
        self.flow_variance_pct = 0.0
        self.anomaly_frequency = 0
        self.flush_irregularity = 0
        self.failure_probability = 0.0
        # True once health has measurably degraded on its own (< 75) — lets the
        # predictive layer distinguish "wear preceded the failure" from "an
        # acute leak is dragging health down".
        self.health_degraded_once = False
        self.anomaly_score = 0
        self.anomaly_band = "NORMAL"
        self.contributing_factors: List[str] = []
        self.pressure_bar = 3.0
        self.cumulative_cycles = 4500

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id, "type": self.type, "zone_id": self.zone_id,
            "zone": self.zone, "terminal": self.terminal, "floor": self.floor,
            "expected_flow_lpm": self.expected_flow_lpm, "flow_lpm": self.flow_lpm,
            "occupancy": self.occupancy, "flush_count": self.flush_count,
            "duration_min": self.duration_min, "sensor_errors": self.sensor_errors,
            "battery_pct": self.battery_pct, "episode_min": self.episode_min,
            "history": list(self.history), "health_score": self.health_score,
            "risk": self.risk, "flow_variance_pct": self.flow_variance_pct,
            "anomaly_frequency": self.anomaly_frequency,
            "flush_irregularity": self.flush_irregularity,
            "failure_probability": self.failure_probability,
            "health_degraded_once": self.health_degraded_once,
            "anomaly_score": self.anomaly_score,
            "anomaly_band": self.anomaly_band,
            "contributing_factors": self.contributing_factors,
            "pressure_bar": self.pressure_bar,
            "cumulative_cycles": self.cumulative_cycles,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DeviceState":
        dev = cls(d["device_id"], d["type"], d["zone_id"], d["zone"],
                  d["terminal"], d["floor"], d.get("expected_flow_lpm", 0.0))
        for k in ("flow_lpm", "occupancy", "flush_count", "duration_min",
                  "sensor_errors", "battery_pct", "episode_min", "health_score",
                  "flow_variance_pct", "anomaly_frequency", "flush_irregularity",
                  "failure_probability", "anomaly_score", "pressure_bar", "cumulative_cycles"):
            setattr(dev, k, d.get(k, 0))
        dev.health_degraded_once = d.get("health_degraded_once", False)
        dev.risk = d.get("risk", "LOW")
        dev.anomaly_band = d.get("anomaly_band", "NORMAL")
        dev.contributing_factors = d.get("contributing_factors", [])
        dev.history = deque(d.get("history", []), maxlen=40)
        return dev


class ZoneState:
    def __init__(self, zone_id: str, name: str, terminal: str, floor: int,
                 base_population: int, threshold: int):
        self.zone_id = zone_id
        self.name = name
        self.terminal = terminal
        self.floor = floor
        self.base_population = base_population
        self.occupancy = 0
        self.threshold = threshold
        self.adaptive_threshold = threshold  # recomputed each tick by the engine
        self.usage_since_cleaning = 0
        self.last_cleaned_min_ago = 0
        self.cleaning_required = False

    def to_dict(self) -> dict:
        return {
            "zone_id": self.zone_id, "name": self.name, "terminal": self.terminal,
            "floor": self.floor, "base_population": self.base_population,
            "occupancy": self.occupancy, "threshold": self.threshold,
            "usage_since_cleaning": self.usage_since_cleaning,
            "last_cleaned_min_ago": self.last_cleaned_min_ago,
            "cleaning_required": self.cleaning_required,
            "adaptive_threshold": self.adaptive_threshold,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ZoneState":
        z = cls(d["zone_id"], d["name"], d["terminal"], d["floor"],
                d["base_population"], d["threshold"])
        z.occupancy = d.get("occupancy", 0)
        z.usage_since_cleaning = d.get("usage_since_cleaning", 0)
        z.last_cleaned_min_ago = d.get("last_cleaned_min_ago", 0)
        z.cleaning_required = d.get("cleaning_required", False)
        z.adaptive_threshold = d.get("adaptive_threshold", z.threshold)
        return z


class Store:
    """All mutable simulation + incident state."""

    def __init__(self) -> None:
        self.devices: Dict[str, DeviceState] = {}
        self.zones: Dict[str, ZoneState] = {}
        self.alerts: List[Alert] = []
        self.tickets: List[MaintenanceTicket] = []
        self.telemetry: deque = deque(maxlen=4000)
        self.timeseries: deque = deque(maxlen=180)
        self.scenarios: Dict[str, dict] = {}  # kind -> {device_id, started_tick, meta}
        self.cleaning_events: List[dict] = []
        self.ticket_seq = 10284
        self.alert_seq = 1
        self.consumed_today_liters = 0.0
        self.saved_month_liters = 0.0
        self.resolved_count = 0
        self.resolved_durations_min: List[float] = []
        self.tick_count = 0
        self.dirty = False
        # writer ownership: devices currently fed by external /telemetry posts
        # (hold_writers) and the tick at which each external stream last wrote.
        self.hold_writers: set = set()
        self.external_writes: Dict[str, int] = {}

    # ---------- persistence ----------
    def save(self) -> None:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        payload = {
            "devices": {k: v.to_dict() for k, v in self.devices.items()},
            "zones": {k: v.to_dict() for k, v in self.zones.items()},
            "alerts": [a.model_dump(mode="json") for a in self.alerts],
            "tickets": [t.model_dump(mode="json") for t in self.tickets],
            "scenarios": self.scenarios,
            "cleaning_events": self.cleaning_events,
            "ticket_seq": self.ticket_seq,
            "alert_seq": self.alert_seq,
            "consumed_today_liters": self.consumed_today_liters,
            "saved_month_liters": self.saved_month_liters,
            "resolved_count": self.resolved_count,
            "resolved_durations_min": self.resolved_durations_min,
            "tick_count": self.tick_count,
        }
        tmp = STATE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmp, STATE_PATH)
        self.dirty = False

    def load(self) -> bool:
        if not os.path.exists(STATE_PATH):
            return False
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                payload = json.load(f)
        except (json.JSONDecodeError, OSError):
            return False
        self.devices = {k: DeviceState.from_dict(v) for k, v in payload.get("devices", {}).items()}
        self.zones = {k: ZoneState.from_dict(v) for k, v in payload.get("zones", {}).items()}
        self.alerts = [Alert(**a) for a in payload.get("alerts", [])]
        self.tickets = [MaintenanceTicket(**t) for t in payload.get("tickets", [])]
        self.scenarios = payload.get("scenarios", {})
        self.cleaning_events = payload.get("cleaning_events", [])
        self.ticket_seq = payload.get("ticket_seq", 10284)
        self.alert_seq = payload.get("alert_seq", 1)
        self.consumed_today_liters = payload.get("consumed_today_liters", 0.0)
        self.saved_month_liters = payload.get("saved_month_liters", 0.0)
        self.resolved_count = payload.get("resolved_count", 0)
        self.resolved_durations_min = payload.get("resolved_durations_min", [])
        self.tick_count = payload.get("tick_count", 0)
        return True

    def reset(self) -> None:
        """Wipe dynamic state (keeps the generated fleet)."""
        self.alerts.clear()
        self.tickets.clear()
        self.telemetry.clear()
        self.timeseries.clear()
        self.scenarios.clear()
        self.cleaning_events.clear()
        self.ticket_seq = 10284
        self.alert_seq = 1
        self.consumed_today_liters = 0.0
        self.saved_month_liters = 0.0
        self.resolved_count = 0
        self.resolved_durations_min.clear()
        self.tick_count = 0
        self.hold_writers.clear()
        self.external_writes.clear()
        for dev in self.devices.values():
            dev.history.clear()
            dev.flow_lpm = 0.0
            dev.episode_min = 0
            dev.sensor_errors = 0
            dev.health_score = 100
            dev.risk = "LOW"
            dev.failure_probability = 0.0
            dev.health_degraded_once = False
        for zone in self.zones.values():
            zone.usage_since_cleaning = 0
            zone.cleaning_required = False
            zone.last_cleaned_min_ago = 0
        self.dirty = True


STORE = Store()
