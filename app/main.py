from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field


app = FastAPI(
    title="KOHLER AquaGuard AI",
    description="Smart Facility & Sustainability Manager API",
    version="0.1.0",
)


class TelemetryEvent(BaseModel):
    device_id: str
    zone: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    flow_lpm: float = Field(ge=0)
    occupancy: int = Field(ge=0, default=0)
    flush_count: int = Field(ge=0, default=0)
    expected_flow_lpm: float = Field(ge=0, default=0)
    duration_min: int = Field(ge=1, default=1)
    temperature_c: Optional[float] = None
    sensor_errors: int = Field(ge=0, default=0)


class Alert(BaseModel):
    id: str
    device_id: str
    zone: str
    issue: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    estimated_loss_liters: float
    estimated_daily_loss_liters: float
    estimated_monthly_loss_liters: float
    diagnosis: str
    recommended_action: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal["OPEN", "RESOLVED"] = "OPEN"


class MaintenanceTicket(BaseModel):
    ticket_id: str
    category: str
    asset: str
    location: str
    issue: str
    severity: str
    estimated_water_loss_daily_liters: float
    action: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DeviceHealth(BaseModel):
    device_id: str
    health_score: int
    anomaly_frequency: int
    flow_variance_pct: float
    flush_irregularity: int
    sensor_errors: int
    predicted_risk_next_7_days: Literal["LOW", "MEDIUM", "HIGH"]


class AIQuery(BaseModel):
    query: str


DEVICES = [
    {"device_id": "FV-182", "type": "Flush Valve", "zone": "Terminal 2 — Restroom 14"},
    {"device_id": "T-204", "type": "Toilet", "zone": "Terminal 1 — Restroom 03"},
    {"device_id": "F-330", "type": "Faucet", "zone": "Terminal 2 — Gate A"},
]
telemetry_store: List[TelemetryEvent] = []
alerts_store: List[Alert] = []
tickets_store: List[MaintenanceTicket] = []
health_store: Dict[str, DeviceHealth] = {}


def _severity_from_daily_loss(daily_loss: float) -> Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
    if daily_loss >= 2500:
        return "CRITICAL"
    if daily_loss >= 1000:
        return "HIGH"
    if daily_loss >= 250:
        return "MEDIUM"
    return "LOW"


def _diagnosis(event: TelemetryEvent, issue: str) -> str:
    if issue == "continuous_leak":
        return (
            f"{event.device_id} has continuous flow ({event.flow_lpm:.2f} L/min) for "
            f"{event.duration_min} minutes with occupancy {event.occupancy} and flush count "
            f"{event.flush_count}. This pattern suggests a likely valve/flush mechanism failure."
        )
    return (
        f"{event.device_id} telemetry indicates elevated anomaly behavior; inspect flow control and sensor health."
    )


def _build_health(event: TelemetryEvent) -> DeviceHealth:
    flow_variance_pct = round(max(0.0, (event.flow_lpm - event.expected_flow_lpm) * 45.0), 2)
    anomaly_frequency = 1 if event.flow_lpm > event.expected_flow_lpm else 0
    flush_irregularity = 1 if event.occupancy == 0 and event.flush_count > 0 else 0
    penalty = int(flow_variance_pct / 4) + (event.sensor_errors * 6) + (anomaly_frequency * 8)
    health_score = max(0, min(100, 100 - penalty))
    if health_score <= 40:
        risk = "HIGH"
    elif health_score <= 70:
        risk = "MEDIUM"
    else:
        risk = "LOW"
    return DeviceHealth(
        device_id=event.device_id,
        health_score=health_score,
        anomaly_frequency=anomaly_frequency,
        flow_variance_pct=flow_variance_pct,
        flush_irregularity=flush_irregularity,
        sensor_errors=event.sensor_errors,
        predicted_risk_next_7_days=risk,
    )


def _process_event(event: TelemetryEvent) -> Optional[Alert]:
    telemetry_store.append(event)
    health_store[event.device_id] = _build_health(event)

    leak_condition = (
        event.flow_lpm > event.expected_flow_lpm
        and event.occupancy == 0
        and event.flush_count == 0
        and event.duration_min >= 5
    )
    if not leak_condition:
        return None

    estimated_loss = round(event.flow_lpm * event.duration_min, 2)
    estimated_daily_loss = round(event.flow_lpm * 60 * 24, 2)
    estimated_monthly_loss = round(estimated_daily_loss * 30, 2)
    severity = _severity_from_daily_loss(estimated_daily_loss)
    diagnosis = _diagnosis(event, "continuous_leak")
    alert = Alert(
        id=f"ALT-{uuid4().hex[:8].upper()}",
        device_id=event.device_id,
        zone=event.zone,
        issue="Continuous water flow detected",
        severity=severity,
        estimated_loss_liters=estimated_loss,
        estimated_daily_loss_liters=estimated_daily_loss,
        estimated_monthly_loss_liters=estimated_monthly_loss,
        diagnosis=diagnosis,
        recommended_action="Dispatch plumbing maintenance immediately.",
    )
    alerts_store.append(alert)

    if severity in {"HIGH", "CRITICAL"}:
        tickets_store.append(
            MaintenanceTicket(
                ticket_id=f"KHL-{uuid4().hex[:5].upper()}",
                category="Plumbing / Water Waste",
                asset=event.device_id,
                location=event.zone,
                issue=alert.issue,
                severity=alert.severity,
                estimated_water_loss_daily_liters=alert.estimated_daily_loss_liters,
                action="Inspect flush valve and inlet mechanism.",
            )
        )
    return alert


@app.get("/devices")
def get_devices() -> Dict[str, List[dict]]:
    return {"devices": DEVICES}


@app.post("/telemetry")
def ingest_telemetry(events: List[TelemetryEvent]) -> Dict[str, object]:
    created_alerts: List[Alert] = []
    for event in events:
        alert = _process_event(event)
        if alert:
            created_alerts.append(alert)
    return {
        "processed": len(events),
        "alerts_created": len(created_alerts),
        "alerts": created_alerts,
    }


@app.get("/alerts")
def get_alerts(status: Optional[Literal["OPEN", "RESOLVED"]] = None) -> Dict[str, List[Alert]]:
    if status:
        return {"alerts": [a for a in alerts_store if a.status == status]}
    return {"alerts": alerts_store}


@app.get("/predictions")
def get_predictions() -> Dict[str, List[DeviceHealth]]:
    return {"device_health": list(health_store.values())}


@app.get("/tickets")
def get_tickets() -> Dict[str, List[MaintenanceTicket]]:
    return {"tickets": tickets_store}


@app.get("/analytics")
def get_analytics() -> Dict[str, object]:
    total_water = round(sum(e.flow_lpm * e.duration_min for e in telemetry_store), 2)
    wasted = round(sum(a.estimated_loss_liters for a in alerts_store if a.status == "OPEN"), 2)
    saved = round(sum(a.estimated_monthly_loss_liters for a in alerts_store if a.status == "RESOLVED"), 2)
    return {
        "kpis": {
            "water_consumption_liters": total_water,
            "active_alerts": len([a for a in alerts_store if a.status == "OPEN"]),
            "devices_at_risk": len([h for h in health_store.values() if h.predicted_risk_next_7_days == "HIGH"]),
            "estimated_monthly_water_saved_liters": saved,
            "estimated_current_wastage_liters": wasted,
        }
    }


@app.post("/ai")
def ai_command_center(body: AIQuery) -> Dict[str, str]:
    q = body.query.lower()
    if not alerts_store:
        return {"response": "No active incidents detected. Facility telemetry is currently within expected ranges."}

    top_alert = max(alerts_store, key=lambda a: a.estimated_daily_loss_liters)
    if "wasting" in q or "waste" in q:
        return {
            "response": (
                f"{top_alert.zone} currently has the highest abnormal consumption via {top_alert.device_id}, "
                f"estimated at {top_alert.estimated_daily_loss_liters:.0f} L/day."
            )
        }
    if "fix first" in q or "priority" in q:
        return {
            "response": (
                f"Prioritize {top_alert.device_id} in {top_alert.zone}. Severity is {top_alert.severity} with "
                f"estimated loss {top_alert.estimated_daily_loss_liters:.0f} L/day."
            )
        }
    return {"response": f"Top incident: {top_alert.device_id} at {top_alert.zone}. {top_alert.diagnosis}"}


@app.post("/simulate/continuous-leak")
def simulate_continuous_leak() -> Dict[str, object]:
    event = TelemetryEvent(
        device_id="FV-182",
        zone="Terminal 2 — Restroom 14",
        flow_lpm=2.7,
        expected_flow_lpm=0,
        duration_min=18,
        occupancy=0,
        flush_count=0,
        sensor_errors=0,
    )
    alert = _process_event(event)
    return {"scenario": "continuous_leak", "event": event, "alert": alert}
