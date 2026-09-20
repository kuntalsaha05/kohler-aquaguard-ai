# KOHLER AquaGuard AI

AI-powered predictive facility operations prototype for Track 2.

## What this prototype demonstrates

Core closed-loop flow:

**Detect → Diagnose → Prioritize → Dispatch → Conserve**

- Real-time telemetry ingestion (`/telemetry`)
- Deterministic continuous leak intelligence (occupancy + flush + flow logic)
- Water loss quantification (current/daily/monthly)
- Predictive device health/risk scoring (`/predictions`)
- AI command-center summaries grounded on computed telemetry (`/ai`)
- Auto-generated maintenance tickets for high-severity incidents (`/tickets`)
- Sustainability KPIs (`/analytics`)
- One-click demo scenario (`/simulate/continuous-leak`)

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs:

- Swagger UI: `http://127.0.0.1:8000/docs`

## Demo flow (2 minutes)

1. Call `POST /simulate/continuous-leak`
2. Check `GET /alerts`
3. Check `GET /tickets`
4. Ask AI:
   - `POST /ai` with `{"query":"Where are we wasting the most water today?"}`
5. View conservation impact:
   - `GET /analytics`