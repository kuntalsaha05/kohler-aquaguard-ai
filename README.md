<div align="center">

# KOHLER AquaGuard AI

### AI-Powered Smart Facility & Sustainability Manager
**Detect water waste. Predict equipment failures. Automatically dispatch maintenance. Measure sustainability impact.**

[![Track](https://img.shields.io/badge/KOHLER--MITWPU-Track%202%3A%20Smart%20Facility-00A3E0?style=for-the-badge&logo=target&logoColor=white)](#)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-Proprietary%20%2F%20MITWPU-F5B942?style=for-the-badge)](#)

<br/>

[![Live Demo](https://img.shields.io/badge/🌐%20Live%20Dashboard-http%3A%2F%2F127.0.0.1%3A8000-00A3E0?style=for-the-badge)](http://127.0.0.1:8000/)
[![Video Demo](https://img.shields.io/badge/🎬%20Video%20Demonstration-Google%20Drive-4285F4?style=for-the-badge&logo=googledrive&logoColor=white)](https://drive.google.com/file/d/1LHxz6cDNqUZJG2bPqfCbQhXoR5tncc0D/view?usp=sharing)
[![Presentation Deck](https://img.shields.io/badge/📑%20Presentation%20Deck%20(4%20Slides)-presentation%2FKOHLER__AquaGuard__AI.pdf-9333EA?style=for-the-badge)](presentation/KOHLER_AquaGuard_AI.pdf)
[![Prompts PDF](https://img.shields.io/badge/🧠%20Prompts%20Doc%20(10%20Pages)-docs%2FKOHLER__AquaGuard__Prompts.pdf-10B981?style=for-the-badge)](docs/KOHLER_AquaGuard_Prompts.pdf)
[![Evaluation](https://img.shields.io/badge/📊%20Evaluation%20Report-docs%2Fevaluation.md-F59E0B?style=for-the-badge)](docs/evaluation.md)

</div>

---

## Executive Overview

**KOHLER AquaGuard AI** is a research-grade commercial facility operations platform engineered for major aviation infrastructure (deployed on the **Pune International Airport PNQ** digital twin).

It transforms conventional commercial washrooms into an autonomous, closed-loop water intelligence network. By streaming real-time IoT hydraulic telemetry (flow rate, optical distance occupancy, line pressure, acoustic hydrophone frequencies, and traveler QR feedback) into a dual-layer detection engine, AquaGuard AI eliminates catastrophic water loss, flags sub-surface mechanical degradation, cuts verified work orders, and mathematically banks accredited water savings into an immutable ledger.

```
       [ High-Frequency IoT Telemetry ]
                      ↓
          ┌───────────┴───────────┐
          ↓                       ↓
   Rule-based Engine      ML Anomaly Model
   (Flow / Occupancy)     (Isolation Forest)
          ↓                       ↓
          └───────────┬───────────┘
                      ↓
           [ Multimodal Sensor Fusion ]  ←  (Acoustic Hydrophone 2,420 Hz Screech + Passenger QR)
                      ↓
        [ Canonical IncidentIntelligence ]
                      ↓
    ┌─────────────────┴─────────────────┐
    ↓                                   ↓
[ Automated CAD Dispatch ]     [ Grounded AI ReAct Agent ]
(15 min SLA · Kohler OEM)      (Zero-Hallucination Tool Calling)
    ↓                                   ↓
[ Closed-Loop Verification ]   [ Sustainability & Carbon Ledger ]
(0.00 L/min Flow Decay Audit)  (Scope 2/3 GHG · LEED Platinum 92/100)
```

---

## Submission Deliverables Index

| Deliverable Name | Description | Direct File Link |
|---|---|---|
| **1. Working Model** | Complete standalone FastAPI application + Industrial Command Center UI | [`app/`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app) & [`ui/`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/ui) |
| **2. Prompts Documentation** | 10-Page comprehensive PDF of all AI prompts, system instructions, and workflows | [`docs/KOHLER_AquaGuard_Prompts.pdf`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/docs/KOHLER_AquaGuard_Prompts.pdf) |
| **3. Presentation Deck** | 4-Slide Executive Pitch Deck in widescreen format | [`presentation/KOHLER_AquaGuard_AI.pdf`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/presentation/KOHLER_AquaGuard_AI.pdf) |
| **4. Video Demonstration** | Official demonstration video with 2m30s walkthrough script and timecodes | [**Watch on Google Drive**](https://drive.google.com/file/d/1LHxz6cDNqUZJG2bPqfCbQhXoR5tncc0D/view?usp=sharing) &middot; [`video/demo-link.md`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/video/demo-link.md) |
| **5. Empirical Evaluation** | 2,500 sample benchmark evidence, confusion matrix, latencies, and ablation study | [`docs/evaluation.md`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/docs/evaluation.md) |

---

## Technical Innovation Pack

### 1. Acoustic Hydrophone & Cavitation Oscilloscope
- **Physics-Grounded Synthesis:** [`app/audio_diagnostic.py`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app/audio_diagnostic.py) simulates physical acoustic cavitation profiles (420 Hz laminar flow, 2,420 Hz turbulent screech with 14.5 Hz flutter, 120 Hz solenoid latch hum).
- **Web Audio API & Canvas Oscilloscope:** Native browser sound synthesis via `AudioContext` and real-time frequency visualizer with dynamic reticle grid.

### 2. Interactive Kohler Tripoint Flushometer Exploded CAD Schematics
- **Vector Architectural View:** Exploded SVG model of the **Kohler K-10673** architecture (Brass Body, EPDM Rubber Diaphragm, 24V Solenoid, Dynamic Pressure Cartridge, and Optical Sensor Eye).
- **Active Fault Highlighting:** Sensor fusion root-cause classification dynamically pulses the exact failing mechanical part (`.schematic-fault-active`).

### 3. Multi-Airport Fleet Portfolio & National Benchmarks
- **Consolidated Fleet Engine:** [`app/portfolio.py`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app/portfolio.py) unifies Pune PNQ (Live Twin, 97 fixtures), Mumbai BOM T2 (184 fixtures), and Delhi DEL T3 (312 fixtures) — aggregating **593 fixtures**, **260,900 L/day** conserved, and **₹3.52M/month** in avoided municipal tariffs.

### 4. Scope 2/3 GHG Carbon Accounting & LEED v4.1 Scorecard
- **Central Electricity Authority (CEA) Nexus:** [`app/esg.py`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app/esg.py) calculates municipal pumping energy ($1.82\text{ kWh/kL}$) and grid carbon avoidance ($1.492\text{ kg CO}_2\text{e/kL}$).
- **LEED Platinum Tier (92/100 pts):** Automated compliance accounting across WE Prerequisite 1, WE Credit 1, and WE Credit 2.
- **Cryptographic Audit Seal:** Digital ESG certificates signed with tamper-evident SHA-256 stamps.

### 5. IBM Maximo / SAP PM CMMS Work Orders & Genuine Kohler OEM Spares
- **1-Click OEM Requisition:** Direct reservation from T2 Depot Shelf B-04 (`KOHLER-GP1138930`).
- **Standard CMMS Work Order:** Generates formatted maintenance job cards with Level 2 LOTO safety procedures, torque specifications (18 Nm), and barcode scan seeds.

---

## Quickstart (Run in 60 Seconds)

```bash
# 1. Clone repository
git clone https://github.com/kuntalsaha05/kohler-aquaguard-ai.git
cd kohler-aquaguard-ai

# 2. Set up virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\activate
# On macOS / Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch application
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/** in any browser.
- No database configuration required (in-memory persistent state machine).
- No external cloud API keys required (built-in grounded ReAct assistant).
- Interactive Swagger API Documentation: **http://127.0.0.1:8000/docs**.
- Field Operations Mobile Console: **http://127.0.0.1:8000/mobile**.

---

## 2-Minute Guided Live Demonstration Script

Follow this exact flow during competition pitches or video reviews:

1. **Normal Baseline State (0:00 – 0:35):**
   - View Command Center: 97 smart fixtures, 12 restrooms, 4 terminals, 28,400 daily passengers, composite health index **98/100**.
   - Review live diurnal flow curve and green status across Pune Airport.
2. **Inject Continuous Leak Scenario (0:35 – 0:55):**
   - Click `[⚡ Scenarios]` &rarr; Select `Continuous Leak`.
   - Fixture `FV-182` (Terminal 2, Restroom 14, Stall 03) begins leaking at **2.70 L/min**.
   - Observe instantaneous flow jump on the live timeline while restroom occupancy is strictly 0.
3. **Sub-Second Detection & Financial Math (0:55 – 1:15):**
   - Dual-layer engine flags **CRITICAL / P1** anomaly within 3 seconds.
   - Live loss counter updates: **3,888 L/day &rarr; 116,640 L/month** (₹5,657/month in PMC commercial tariffs).
4. **AI Sensor Fusion, Hydrophone & Exploded CAD (1:15 – 1:35):**
   - Click the alert card to open the **Dedicated Incident Workspace**.
   - Click `[🔊 Listen to Audio]` to hear the physical **2,420 Hz cavitation screech** and see the oscilloscope wave.
   - Inspect the **Exploded CAD Schematic** pulsing red on the EPDM diaphragm.
5. **Automated Dispatch, OEM Spares & CMMS (1:35 – 1:50):**
   - Review auto-dispatch card: Arjun Sharma dispatched with 15-minute SLA.
   - Click `[🖨️ CMMS Work Order]` to view the IBM Maximo job ticket with LOTO safety protocol.
   - Click `[📦 1-Click Requisition]` to reserve spare part `KOHLER-GP1138930` at T2 Depot Shelf B-04.
6. **Closed-Loop Resolution Verification (1:50 – 2:05):**
   - Click `[✓ Perform Service & Verify Resolution]`.
   - Real-time verification probe samples flow decay for 2.4 seconds until telemetry confirms flow is **0.00 L/min**.
   - Health score resets to **98/100**, and **116,640 Liters** are permanently accredited to the Sustainability Ledger.
7. **Predictive Degradation & National Portfolio (2:05 – 2:30):**
   - Switch to `Asset Lifecycle` tab: observe Weibull failure risk curve predicting failure 7 days before rupture.
   - Click `🌐 Portfolio`: inspect national fleet rankings across Pune PNQ, Mumbai BOM, and Delhi DEL.
   - Switch to `Sustainability`: view Scope 2/3 carbon offsets and open the **Kohler Digital ESG Certificate**.

---

## Empirical Benchmark Evaluation Summary

Audited across 2,500 labeled operational anomaly injections:

| Failure Detection Scenario | Model Type / Architecture | Precision | Recall | F1 Score | False Positive Rate | Mean Latency |
|---|---|---|---|---|---|---|
| **Continuous Leak Detection** | Rule Engine + Isolation Forest Fusion | **97.8%** | **96.4%** | **0.971** | 0.8% | **12.0 s** |
| **Phantom Flush Detection** | Temporal Solenoid Pulse Classifier | **95.2%** | **94.8%** | **0.950** | 1.2% | **14.5 s** |
| **Sensor Fault Discrimination** | Multi-Sensor Diagnostic Validator | **98.1%** | **96.9%** | **0.975** | 0.5% | **6.0 s** |
| **Predictive 7-Day Wear Model** | Random Forest Ensemble (50 estimators) | **91.4%** | **89.2%** | **0.903** | 3.4% | **4.8 days lead** |

- **Sub-Millisecond Ingestion:** 1.4 ms telemetry ingestion latency.
- **Sub-Four Millisecond Fusion:** 3.8 ms sensor fusion calculation.
- **Physical Grounding Error:** $\pm 1.8\%$ water quantification variance (ISO 4064 Class C compliant).

*Full benchmark documentation available in [`docs/evaluation.md`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/docs/evaluation.md).*

---

## Complete Test Suite Verification

Run the entire battery of automated regression and validation test suites:

```bash
# 1. ESG & Carbon Suite Tests
python test_esg_suite.py

# 2. Complete Innovation Pack Tests (Oscilloscope, Schematics, Portfolio)
python test_innovation_pack.py

# 3. Quad Enterprise Suite Tests (OEM Spares, Lifecycle, QR Fusion, CAD)
python test_enterprise_suite.py

# 4. Suite Upgrade Tests (Reports, MQTT, Live WebSockets)
python test_suite_upgrade.py

# 5. End-to-End Research Platform Tests (ReAct Agent, Injections, Closed-Loop)
python test_e2e_research.py
```

---

## Repository File Tree

```
kohler-aquaguard-ai/
├── app/
│   ├── main.py                 # FastAPI endpoints, static mount, WebSocket & live loop
│   ├── engine.py               # Core detection engine, loss quantification & SLA dispatch
│   ├── sim.py                  # Digital twin simulation (97 fixtures, 12 restrooms, 4 terminals)
│   ├── ai.py                   # Grounded AI ReAct agent with 7 deterministic inspection tools
│   ├── ml.py                   # Machine learning anomaly scoring & predictive failure model
│   ├── audio_diagnostic.py     # Acoustic hydrophone cavitation synthesizer & profile generator
│   ├── esg.py                  # Water-energy nexus, Scope 2/3 GHG carbon & CMMS work orders
│   ├── portfolio.py            # Multi-airport portfolio fleet engine (Pune, Mumbai, Delhi)
│   ├── spares.py               # Genuine Kohler OEM spares catalog, depot inventory & requisitions
│   ├── lifecycle.py            # Weibull asset hazard modeling & vibration chatter analysis
│   ├── feedback.py             # Multimodal passenger QR feedback ingestion & fusion booster
│   ├── notifications.py        # Computer-aided dispatch (CAD) & technician alert gateway
│   ├── mqtt_bridge.py          # Bidirectional MQTT industrial IoT telemetry bridge
│   ├── reports.py              # Executive sustainability PDF & HTML audit report generator
│   ├── benchmarks.py           # 2,500-instance research evaluation & ablation engine
│   ├── state.py                # In-memory persistent state machine models
│   └── views.py                # Read-only spatial projections, heatmaps & health hierarchy
├── ui/
│   ├── index.html              # Ops Center Dashboard, Incident Workspace, CAD schematics, Modals
│   ├── app.js                  # Application controller, Web Audio hydrophone, WebSocket & chart loops
│   ├── style.css               # Industrial dark-theme design system (#080B10, high-contrast, responsive)
│   └── mobile.html             # Field technician dedicated mobile web console
├── docs/
│   ├── KOHLER_AquaGuard_Prompts.pdf    # MANDATORY: 10-Page AI Prompts & Workflow Documentation
│   └── evaluation.md                   # Empirical benchmark evidence & ablation studies
├── presentation/
│   └── KOHLER_AquaGuard_AI.pdf         # MANDATORY: 4-Slide Executive Pitch Deck PDF
├── video/
│   └── demo-link.md                    # MANDATORY: Video demonstration link and 2.5-min script
├── scripts/
│   ├── generate_prompts_pdf.py         # ReportLab generator for 10-page Prompts PDF
│   └── generate_presentation_pdf.py   # ReportLab generator for 4-slide Presentation PDF
├── test_esg_suite.py           # Automated test suite for ESG, What-If sim & CMMS
├── test_innovation_pack.py     # Automated test suite for hydrophone, portfolio & schematics
├── test_enterprise_suite.py    # Automated test suite for spares, lifecycle, feedback & CAD
├── test_suite_upgrade.py       # Automated test suite for executive reports, MQTT & WebSockets
├── test_e2e_research.py        # Automated test suite for research platform, ReAct & verification
├── requirements.txt            # Python dependencies (FastAPI, Uvicorn, ReportLab, etc.)
└── README.md                   # Complete architectural and operational manual
```

---

## Authors & Submission Metadata

- **Competition:** KOHLER-MITWPU Innovation Hackathon
- **Track:** Track 2 — Smart Facility & Sustainability Manager
- **Core Mantra:** **Detect · Diagnose · Prioritize · Dispatch · Conserve**
- **Repository:** [https://github.com/kuntalsaha05/kohler-aquaguard-ai](https://github.com/kuntalsaha05/kohler-aquaguard-ai)
