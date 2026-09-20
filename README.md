# KOHLER AquaGuard AI

**AI-powered predictive facility operations — Smart Facility & Sustainability Manager (Track 2)**

> Detect → Diagnose → Prioritize → Dispatch → Conserve

A working end-to-end prototype: a simulated **digital twin** of an airport
(97 instrumented fixtures across 12 restrooms, 4 terminals) streams live
telemetry into a deterministic detection engine that quantifies water loss,
scores device health, explains incidents, and **auto-generates prioritized
maintenance tickets** — with a live ops-center dashboard and a grounded
AI command center.

---

## Quickstart (60 seconds)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/** — the dashboard starts streaming immediately
(no build step, no database, no API keys).

API docs: http://127.0.0.1:8000/docs

## The 2-minute demo script

1. **Normal state** — show the dashboard: all-green facility map, healthy KPIs.
2. Click **💧 Continuous leak** in the toolbar. The scenario targets
   **FV-182, Terminal 2 — Restroom 14** (flush valve stuck open).
3. Watch the flow chart and incident feed — after ~12 seconds
   (5 simulated minutes of sustained idle flow) the system raises
   **CRITICAL / P1: continuous flow, zero occupancy, zero flushes**, with the
   loss math: `2.7 L/min × 1,440 = ~3,888 L/day → ~116,640 L/month`.
4. Click the alert card → **AI diagnosis** explains the fault and the exact
   estimation; a **dispatch ticket (KHL-…)** was already auto-generated.
5. Ask the AI Command Center: *"Where are we wasting the most water today?"*
   and *"What should I fix first?"* — answers are computed from live data.
6. Click **✓ Resolve & verify** on the ticket — **resolution is the
   authoritative fix**: the leak scenario ends (no re-fire), FV-182's health
   model resets to baseline, **116,640 L/month** moves into the sustainability
   ledger (~778 household-days of water), and any sibling incidents on the
   same fixture close with the service visit.
7. Show **Predictive Maintenance**: inject **📉 Device degradation** and watch
   health scores decay, failure probability climb, and a predictive alert fire
   *before* the degradation ripens into a sustained leak — the predictive
   ticket coexists with the later leak alert because wear came first.
8. Try the other scenarios: **🚽 Phantom flushes** (solenoid fault),
   **🔌 Sensor failure** (telemetry flatline), **👥 Occupancy spike**
   (adaptive hygiene threshold breach → housekeeping ticket → **🧹 Mark
   cleaned** resolves it).
9. Or press **▶ Run guided demo** and let the dashboard narrate itself:
   leak → detection → AI Q&A → diagnosis modal → resolve → savings ledger,
   ending at **0 open incidents** with the monthly loss avoided on screen.

### External telemetry (real IoT ingestion)

`POST /telemetry` accepts real device events and runs the same detection
pipeline. External streams claim their devices' writer slot (the simulator
pauses those devices), detection fires after 5 sustained ticks (~10 s at
1 post/second), and the simulator resumes ownership 5 ticks after the
external stream goes quiet — one writer per device, never interleaved.

## Architecture

```
ui/            Ops-center dashboard (Terminal Twin + Incident Timeline + Report Generator)
app/
  main.py      FastAPI: API + static UI + simulation loop (1 tick ≈ 1 sim minute / 2 s)
  ml.py        ML engine: 0-100 Anomaly scoring + trained 7-day failure risk model (RandomForest)
  sim.py       Digital twin: 97 fixtures across 4 terminals + 7 scenario injectors
  engine.py    Core: detection, loss math, SLA dispatch optimization, timeline tracking
  views.py     Read-only projections: digital twin status, KPI rollups, device status
  ai.py        Grounded AI Agent: ReAct tool-calling loop, cost-of-inaction simulations, reports
  state.py     Data models + persisted store with SLA and lifecycle milestones
```

Detection & Operations pipeline per tick:

```
telemetry → composite anomaly scoring (0-100) → detectors → loss estimation
          → ML failure risk model → severity → priority (P1–P4)
          → alert & chronological timeline upsert → SLA dispatch optimizer (technician routing)
          → resolution verification → sustainability & cost ledger
```

### The AI & ML Architecture

| Layer | Implementation | Purpose |
|---|---|---|
| Rule-based detection | `engine.py` (`flow > 0` ∧ `occupancy == 0` ∧ `flushes == 0` for 5+ min) | Obvious faults, zero false positives |
| Composite Anomaly Score | `ml.py` (0–100 scale: NORMAL, WATCH, ANOMALOUS, CRITICAL) | Multi-factor telemetry variance & mismatch quantification |
| ML Predictive Maintenance | `ml.py` (`RandomForestClassifier` trained on facility history) | 7-day failure probability + feature importance breakdown |
| Grounded ReAct Agent | `ai.py` (Deterministic tool-calling loop over live twin) | Q&A, inaction cost simulations, daily intelligence reports |
| SLA Dispatch Optimizer | `engine.py` (Technician routing based on skill, proximity, load) | Automated assignment with 15m/45m/90m SLA deadlines |

**Design rule:** every number is computed deterministically or by trained statistical models — the reasoning layer explains telemetry and acts on live tools, it never invents data.

## Detection & Operational Capabilities

- **Continuous leak intelligence** — idle flow with zero occupancy/flushes; quantified daily/monthly losses.
- **Phantom flushes** — ghost activations with zero occupancy (solenoid seal failure).
- **Sensor failure** — flatline telemetry, frozen occupancy, and climbing error rates.
- **Device degradation & ML risk** — trained Random Forest predicts 7-day failure probability with attributed feature importance (idle flow frequency, flow variance, cycle fatigue).
- **Pressure anomaly** — sudden line pressure drop below 1.5 bar accompanied by a surge in flow (supply riser breach).
- **Multi-leak storm** — concurrent leaks across terminals testing automated P1/P2/P3 prioritization and technician dispatch.
- **SLA-aware dispatch optimization** — auto-routes certified technicians (Plumbing, Electrical/IoT, Housekeeping) with proximity-based ETAs and SLA enforcement timers.
- **Incident lifecycle timeline** — step-by-step chronological audit trail (`ANOMALY_CONFIRMED` → `DISPATCH_OPTIMIZED` → `VERIFIED_RESOLUTION`).
- **Cost of Inaction simulation** — projects 7-day and 30-day water loss and tariff expense if left unfixed vs 15m AI automated response.
- **Executive Daily Report** — one-click printable briefing with water saved, tariff costs avoided, and compliance metrics.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/state` | Full dashboard snapshot (KPIs, terminal zones, alerts, tickets, risk, timeseries) |
| GET | `/api/report` | Daily facility intelligence summary report |
| POST | `/telemetry` | External telemetry ingestion (same pipeline) |
| GET | `/alerts` · `/tickets` · `/devices` · `/predictions` | Incident and device queries |
| POST | `/alerts/{id}/resolve` · `/tickets/{id}/resolve` | Verified resolution & sustainability ledger updates |
| POST | `/zones/{id}/cleaned` | Record zone cleaning |
| POST | `/ai` | Grounded command center ReAct agent (`{"query": "..."}`) |
| POST | `/simulate/{scenario}` | Inject `continuous-leak` \| `phantom-flushes` \| `device-degradation` \| `pressure-anomaly` \| `multiple-leaks` \| `sensor-failure` \| `occupancy-spike` |
| POST | `/simulate/stop` · `/simulate/reset` | Scenario control |
| GET | `/healthz` | System health and simulation uptime |

## Notes

- State persists to `data/state.json` every 15 ticks; delete the file (or
  `POST /simulate/reset`) for a pristine demo.
- Hygiene counters are seeded at boot so the facility looks lived-in;
  thresholds (~2,600 interactions) make breaches meaningful, not constant.
- The simulation clock compresses time: 2 s real ≈ 1 facility minute, so a
  5-minute leak-detection threshold fires in ~12 seconds of demo time.
- Reset (`POST /simulate/reset`) re-seeds lived-in hygiene counters so
  scenario demos behave identically from a fresh boot or a reset.

---

**From reactive maintenance to autonomous facility intelligence.**
