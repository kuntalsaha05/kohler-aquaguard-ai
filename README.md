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
ui/            Ops-center dashboard (vanilla JS + canvas, zero build)
app/
  main.py      FastAPI: API + static UI + simulation loop (1 tick ≈ 1 sim minute / 2 s)
  sim.py       Digital twin: fleet generator, airport traffic curve, 5 scenario injectors
  engine.py    Deterministic core: detectors, loss math, health model, priority, dispatch
  views.py     Read-only projections: dashboard snapshot, KPI rollup, device status
  ai.py        Explanation layer: diagnosis composer + grounded command-center Q&A
  state.py     Models + JSON-persisted store (data/state.json survives restarts)
```

Detection pipeline per tick:

```
telemetry → detectors → loss estimation → severity → priority (P1–P4)
          → alert upsert/escalation → auto-dispatch ticket → health model
          → resolution verification → sustainability ledger
```

### The four AI layers

| Layer | Implementation | Purpose |
|---|---|---|
| Rule-based detection | `engine.py` (`flow > 0` ∧ `occupancy == 0` ∧ `flushes == 0` for 5+ min) | Obvious faults, zero false positives |
| Anomaly detection | rolling-window statistics: idle-flow mean, flow variance, flush irregularity | Unusual telemetry patterns |
| Predictive maintenance | health scoring model → 7-day failure probability → predictive alerts | Fix devices before they fail |
| Reasoning/explanation | `ai.py` composer (deterministic; swappable for an LLM call with the same structured facts) | Incident diagnosis, ticket text, NL Q&A |

**Design rule:** every number is computed deterministically — the reasoning
layer explains telemetry, it never invents data.

## Detection capabilities

- **Continuous leak intelligence** — idle flow with zero occupancy/flushes;
  quantified so-far / daily / monthly loss; escalates with duration
- **Phantom flushes** — flush events with zero occupancy (solenoid fault);
  loss = rate × 6 L/flush
- **Sensor failure** — flatlined telemetry, frozen occupancy, climbing errors
- **Device degradation** — health score from anomaly frequency, idle flow,
  variance, irregular flushes, sensor errors → LOW/MEDIUM/HIGH 7-day risk
- **Adaptive hygiene engine** — per-zone usage threshold that flexes with
  occupancy pressure and time-since-cleaning; auto housekeeping tickets;
  cleaning events reset the counter
- **Priority engine** — P1–P4 from severity + loss rate; CRITICAL leak → P1
  immediate dispatch; tickets stay synced when incidents escalate
- **Authoritative resolution** — resolving an alert/ticket ends that device's
  fault scenario (no re-fire), service-resets the health model, and closes
  sibling water-loss incidents on the same fixture (banking their savings)
- **Predictive-before-failure** — devices whose health degrades on their own
  (`health_degraded_once`) earn a predictive alert even after a leak develops
  from the wear; acute leaks that drag health down do not double-alert

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/state` | Full dashboard snapshot (KPIs, zones, alerts, tickets, risk, timeseries) |
| POST | `/telemetry` | External telemetry ingestion (same pipeline) |
| GET | `/alerts` · `/tickets` · `/devices` · `/predictions` | Incident/domain queries (`?status=OPEN`) |
| POST | `/alerts/{id}/resolve` · `/tickets/{id}/resolve` | Resolve + verification + ledger |
| POST | `/zones/{id}/cleaned` | Record cleaning |
| POST | `/ai` | Command center (`{"query": "..."}`) |
| POST | `/simulate/{scenario}` | Inject `continuous-leak` \| `phantom-flushes` \| `device-degradation` \| `sensor-failure` \| `occupancy-spike` |
| POST | `/simulate/stop` · `/simulate/reset` | Scenario control |
| GET | `/analytics` · `/healthz` | KPIs · liveness |

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
