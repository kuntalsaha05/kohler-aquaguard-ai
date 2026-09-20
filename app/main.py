"""KOHLER AquaGuard AI — Smart Facility & Sustainability Manager API.

Run:  uvicorn app.main:app --reload   (from project root)
UI:   http://127.0.0.1:8000/
Docs: http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ai, benchmarks, engine, sim, views
from .state import (
    SIM_INTERVAL_SECONDS,
    Store,
    TelemetryEvent,
    STORE,
    utcnow,
)

UI_DIR = os.path.join(os.path.dirname(__file__), "..", "ui")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not STORE.load():
        sim.build_fleet(STORE)
    else:
        sim.build_fleet(STORE)  # ensure fleet matches current blueprint
    task = asyncio.create_task(_simulation_loop())
    yield
    task.cancel()
    STORE.save()


async def _simulation_loop() -> None:
    while True:
        try:
            engine._expire_external_writers(STORE)
            events = sim.generate_tick(STORE)
            engine.process_events(STORE, events)
            if STORE.dirty and STORE.tick_count % 15 == 0:
                STORE.save()
        except Exception as exc:  # keep the twin alive no matter what
            print(f"[sim] tick error: {exc!r}")
        await asyncio.sleep(SIM_INTERVAL_SECONDS)


app = FastAPI(
    title="KOHLER AquaGuard AI",
    description="Smart Facility & Sustainability Manager — detect, diagnose, prioritize, dispatch, conserve.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


class AIQuery(BaseModel):
    query: str


# ------------------------------------------------------------------ UI

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(os.path.join(UI_DIR, "index.html"))


app.mount("/ui", StaticFiles(directory=UI_DIR), name="ui")


# -------------------------------------------------------------- realtime

@app.get("/api/state")
def get_state() -> dict:
    return views.facility_snapshot(STORE)


@app.get("/api/timeseries")
def get_timeseries() -> dict:
    return {"points": list(STORE.timeseries)}


@app.get("/api/incidents")
def get_incidents() -> dict:
    return {"incidents": [i.model_dump(mode="json") for i in reversed(STORE.incidents[-50:])]}


@app.get("/api/facility-health")
def get_facility_health() -> dict:
    return views.facility_health_hierarchy(STORE)


@app.get("/api/heatmap")
def get_heatmap() -> dict:
    return {"heatmap": views.water_waste_heatmap(STORE)}


@app.get("/api/evaluation")
def get_evaluation() -> dict:
    return benchmarks.get_evaluation_metrics()


# ------------------------------------------------------------- telemetry

@app.post("/telemetry")
def ingest_telemetry(events: List[TelemetryEvent]) -> dict:
    """External telemetry ingestion — same pipeline, external writer priority.

    External events claim their devices' writer slots (the simulator pauses
    those devices) and detection runs immediately; after 5 ticks of silence
    the simulator resumes ownership. Sustained posting reaches the 5-tick
    leak threshold in ~10 seconds of wall clock.
    """
    result = engine.process_events(STORE, events, external=True)
    return {
        "processed": len(events),
        "alerts_created": len(result["new_alerts"]),
        "tickets_created": len(result["new_tickets"]),
        "alerts": [a.model_dump(mode="json") for a in result["new_alerts"]],
        "tickets": [t.model_dump(mode="json") for t in result["new_tickets"]],
    }


@app.get("/devices")
def get_devices() -> dict:
    return {"devices": [
        {
            "device_id": d.device_id, "type": d.type, "zone": d.zone,
            "terminal": d.terminal, "floor": d.floor,
            "flow_lpm": round(d.flow_lpm, 2), "occupancy": d.occupancy,
            "health_score": d.health_score, "risk": d.risk,
        }
        for d in STORE.devices.values()
    ]}


# ----------------------------------------------------------------- incidents

@app.get("/alerts")
def get_alerts(status: Optional[str] = None) -> dict:
    alerts = STORE.alerts
    if status:
        alerts = [a for a in alerts if a.status == status.upper()]
    return {"alerts": [a.model_dump(mode="json") for a in reversed(alerts[-60:])]}


@app.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str) -> dict:
    alert = engine.resolve_alert(STORE, alert_id)
    if not alert:
        raise HTTPException(404, "Open alert not found")
    return {"resolved": alert.id,
            "resolution_note": alert.resolution_note,
            "saved_month_liters": round(STORE.saved_month_liters, 1)}


@app.get("/tickets")
def get_tickets() -> dict:
    return {"tickets": [t.model_dump(mode="json") for t in reversed(STORE.tickets[-40:])]}


@app.post("/tickets/{ticket_id}/resolve")
def resolve_ticket(ticket_id: str) -> dict:
    ticket = engine.resolve_ticket(STORE, ticket_id)
    if not ticket:
        raise HTTPException(404, "Open ticket not found")
    return {"resolved": ticket.ticket_id,
            "linked_alert_resolved": True,
            "saved_month_liters": round(STORE.saved_month_liters, 1)}


@app.post("/zones/{zone_id}/cleaned")
def zone_cleaned(zone_id: str) -> dict:
    event = engine.record_cleaning(STORE, zone_id)
    if not event:
        raise HTTPException(404, "Zone not found")
    return {"cleaning_recorded": event}


@app.get("/predictions")
def get_predictions() -> dict:
    risky = sorted(STORE.devices.values(), key=lambda d: d.health_score)[:30]
    return {"device_health": [
        {
            "device_id": d.device_id, "type": d.type, "zone": d.zone,
            "health_score": d.health_score, "risk": d.risk,
            "failure_probability_7d": d.failure_probability,
            "flow_variance_pct": round(d.flow_variance_pct, 1),
            "anomaly_frequency": d.anomaly_frequency,
            "flush_irregularity": d.flush_irregularity,
            "sensor_errors": d.sensor_errors,
        } for d in risky
    ]}


# ------------------------------------------------------------- analytics

@app.get("/analytics")
def get_analytics() -> dict:
    snap = views.facility_snapshot(STORE)
    kpis = snap["kpis"]
    return {
        "kpis": {
            "water_consumption_liters": kpis["water_consumption_liters"],
            "active_alerts": kpis["active_alerts"],
            "devices_at_risk": kpis["devices_at_risk"],
            "estimated_monthly_water_saved_liters": kpis["water_saved_month_liters"],
            "estimated_current_wastage_liters": kpis["current_wastage_liters"],
            "incidents_resolved": kpis["incidents_resolved"],
            "mttr_minutes": kpis["mttr_minutes"],
        },
        "sustainability": {
            "saved_month_liters": kpis["water_saved_month_liters"],
            "household_days_equivalent": round(kpis["water_saved_month_liters"] / 150.0, 1),
            "open_wastage_liters": kpis["current_wastage_liters"],
            "avg_device_health": kpis["avg_device_health"],
        },
    }


# ------------------------------------------------------------------- AI

@app.post("/ai")
def ai_command_center(body: AIQuery) -> dict:
    result = ai.command_center_answer(STORE, body.query)
    return {
        "response": result["response"],
        "tool_trail": result.get("tool_trail", []),
        "report_data": result.get("report_data"),
        "engine": "Grounded AI Facility Agent (Deterministic ReAct Loop)",
        "ts": utcnow().isoformat(),
    }


@app.get("/api/report")
def get_facility_report() -> dict:
    return ai._tool_generate_facility_report(STORE)



# ------------------------------------------------------------- simulation
# NOTE: static paths must be declared before the dynamic /simulate/{scenario}
# route, or FastAPI matches "stop"/"reset" as a scenario name.

@app.post("/simulate/stop")
def stop_scenarios() -> dict:
    sim.stop_all_scenarios(STORE)
    STORE.hold_writers.clear()
    STORE.dirty = True
    return {"stopped": True, "active_scenarios": 0}


@app.post("/simulate/reset")
def reset_simulation() -> dict:
    sim.stop_all_scenarios(STORE)
    STORE.reset()
    sim.seed_hygiene_counters(STORE)
    STORE.save()
    return {"reset": True}


@app.post("/simulate/{scenario}")
def inject_scenario(scenario: str, device_id: Optional[str] = None) -> dict:
    try:
        result = sim.start_scenario(STORE, scenario, device_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    STORE.dirty = True
    return {"injected": True, "sim_minutes": STORE.tick_count, **result}


@app.get("/healthz")
def healthz() -> JSONResponse:
    return JSONResponse({"ok": True, "sim_minutes": STORE.tick_count})
