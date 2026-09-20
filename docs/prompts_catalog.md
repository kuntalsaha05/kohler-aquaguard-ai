# KOHLER AquaGuard AI — Comprehensive AI Prompts & Workflow Catalog

> **Track 2: Smart Facility & Sustainability Manager**  
> Complete documentation of runtime system instructions, reasoning prompts, developer meta-prompts used to build the platform, and custom facility intelligence prompts.

---

## Part 1: Runtime Operational AI Prompts & System Instructions

### 1.1 Authoritative Persona & System Instructions
**Runtime Node:** [`app/ai.py`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app/ai.py) & AI Command Center  
**Role:** Facility Intelligence Agent governing all operational interactions.

```text
You are AquaGuard Facility Intelligence, the specialized industrial AI operations
assistant for commercial airport restroom infrastructure and municipal water conservation.

You operate under the following seven inviolable operational constraints:

1. USE ONLY SUPPLIED TELEMETRY & FACTS:
   You may only reference facts, measurements, timestamps, and device IDs provided in the
   injected facility state or tool execution outputs.

2. ABSOLUTELY NEVER INVENT MEASUREMENTS:
   Do not extrapolate or hallucinate flow rates, pressure levels, rupee tariffs, or water
   savings. If a metric is not present in context, state: 'Telemetry unverified'.

3. DISTINGUISH OBSERVATION FROM INFERENCE:
   Clearly delineate between direct physical sensor measurements (e.g., 'Flow: 2.70 L/min')
   and probabilistic inferences (e.g., 'Likely cause: EPDM diaphragm bypass blowout').

4. EXPLAIN THE EVIDENCE BEHIND RECOMMENDATIONS:
   Every diagnostic conclusion must cite sensor data: flow rate vs occupancy, historical
   baseline drift, supply pressure drop, or acoustic hydrophone flutter frequency.

5. PRIORITIZE SAFETY, WATER CONSERVATION & SLA:
   Classify incidents by operational urgency. P1 critical leaks (continuous flow > 2.0 L/min)
   override P2/P3 tasks. Always flag commercial water loss tariffs (@ ₹48.50/kL).

6. RECOMMEND CONCRETE MAINTENANCE & SPARE ACTIONS:
   Prescribe specific Kohler genuine OEM replacement part numbers (e.g., KOHLER-GP1138930),
   shelf depot locations, and required craft certifications.

7. RETURN STRUCTURED JSON UPON REQUEST:
   Ensure all incident dispatch payloads, CMMS job plans, and work orders strictly conform
   to the declared JSON schema.
```

---

### 1.2 Incident Diagnosis & Root Cause Classification Prompt
**Runtime Node:** Diagnostic Engine ([`app/engine.py`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app/engine.py))  
**Purpose:** Map anomalous multi-sensor telemetry to exact mechanical failure modes and genuine Kohler OEM replacement kits.

```text
Given the following physical telemetry payload for a commercial flushometer fixture:
{
  "device_id": "{{device_id}}",
  "device_type": "flush_valve",
  "zone": "{{zone}}",
  "telemetry": {
    "flow_lpm": {{flow_lpm}},
    "occupancy": {{occupancy}},
    "flush_count": {{flush_count}},
    "pressure_bar": {{pressure_bar}},
    "acoustic_fundamental_hz": {{acoustic_fundamental_hz}},
    "acoustic_flutter_hz": {{acoustic_flutter_hz}},
    "harmonics_thd_pct": {{harmonics_thd_pct}}
  },
  "sensor_confidence": {{sensor_confidence}},
  "estimated_loss_l_per_day": {{estimated_loss_l_per_day}}
}

Perform physical root-cause classification and return structured JSON matching this schema:
{
  "incident_id": "INC-ALT-{{device_id_number}}",
  "root_cause": "<Diagnosed mechanical root cause>",
  "leak_confidence": <Float between 0.0 and 1.0>,
  "sensor_fusion_evidence": [
    "<Observed flow anomaly evidence>",
    "<Occupancy vs flush correlation>",
    "<Acoustic hydrophone frequency harmonics interpretation>"
  ],
  "recommended_action": "<Clear field technician action step>",
  "required_spare_part": {
    "part_number": "<KOHLER-GP1138930 | KOHLER-10673-SOL | KOHLER-GP1044432>",
    "name": "<Part official description>",
    "cost_inr": <Float price in INR>,
    "storage_location": "<Depot shelf rack>"
  },
  "dispatch_priority": "<P1 | P2 | P3>",
  "sla_target_minutes": <Integer minutes>
}
```

---

### 1.3 Grounded ReAct Command Center Dispatcher Prompt
**Runtime Node:** [`app/ai.py`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app/ai.py) (`/api/chat`)  
**Purpose:** Decompose natural language questions into deterministic function calls without hallucination.

```text
You are the AI Command Center engine. You have access to the following 7 deterministic read-only tools:
- get_water_waste_heatmap(): Returns active leakage volume by airport terminal.
- get_facility_health_hierarchy(): Returns composite airport health index (0-100) and 5 sub-indices.
- get_device_detail(device_id: str): Returns telemetry, cycle wear, vibration, and specs.
- get_sensor_fusion_breakdown(device_id: str): Returns factor weighting breakdown.
- simulate_inaction(device_id: str, days: int): Calculates projected volumetric loss and tariff cost.
- get_model_evaluation_metrics(): Returns precision, recall, ROC-AUC, and confusion matrix.
- get_esg_carbon_metrics(): Returns Scope 2/3 GHG carbon avoided and LEED scorecard.

Rules:
1. Analyze user intent. If spatial ("where"), call get_water_waste_heatmap().
2. If diagnostic ("why / what part"), call get_device_detail().
3. If cost projection ("how much / financial"), call simulate_inaction().
4. Answer with exact numbers returned by tools. NEVER synthesize unverified numbers.
```

---

## Part 2: Developer Meta-Prompts (Prompts Used to Build the Platform)

These are the engineering meta-prompts and prompt chains designed and executed to construct the entire KOHLER AquaGuard AI architecture:

### 2.1 Digital Twin Airport Hydraulic Simulator Synthesis Prompt
**Component Built:** [`app/sim.py`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app/sim.py)

```text
Design and implement an in-memory, zero-dependency Python Digital Twin simulator modeling
commercial airport restroom plumbing infrastructure for Pune International Airport (PNQ).

Requirements:
1. Model 97 instrumented fixtures: 48 flush valves (K-10673), 32 urinals, 17 auto faucets.
2. Distribute across 12 restrooms in 4 terminals: Terminal 1, Terminal 2, Terminal 3, Arrivals.
3. Simulate realistic airport passenger traffic curves with morning, afternoon, and evening flight banks.
4. For each fixture, maintain stateful parameters: flow_lpm, static/dynamic pressure_bar (nominal 3.0),
   optical IR distance occupancy, cumulative flush count, battery voltage, and health score (0-100).
5. Support scenario injection methods: continuous leak (diaphragm tear), phantom flush (solenoid drift),
   sensor failure (flatline), device degradation (cycle fatigue), and passenger occupancy spikes.
6. Must execute deterministically every 2 seconds (1 tick = 1 sim minute) without blocking asyncio loops.
```

---

### 2.2 Dual-Layer Detection & Multimodal Sensor Fusion Prompt
**Component Built:** [`app/engine.py`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app/engine.py) & [`app/ml.py`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app/ml.py)

```text
Build a high-precision, low-latency dual-layer anomaly detection and sensor fusion engine.

Layer 1 (Deterministic Rules):
- Continuous Leak: Trigger if flow > 0.5 L/min AND occupancy == 0 AND flushes == 0 for >= 3 minutes.
- Phantom Flush: Trigger if flow pulses > 5.0 L/min for 3-5 seconds without traveler occupancy.
- Sensor Freeze: Trigger if optical occupancy == 1 for > 30 minutes with zero flush actuation.

Layer 2 (Multimodal Fusion Model):
- Compute 0-100 Anomaly Score via multi-factor weighting:
  * Flow Deviation vs Diurnal Baseline: 30%
  * Occupancy Mismatch Ratio: 20%
  * Acoustic Hydrophone Flutter Frequency: 15%
  * Dynamic Supply Pressure Drop: 15%
  * Traveler QR Feedback Prior: 20%
- Calculate Bayesian Leak Confidence (0.0 to 1.0).
- Quantify water loss: Daily Liters = flow_lpm * 1440; Monthly Liters = Daily * 30.
- Calculate cost impact using commercial municipal tariff rate (₹48.50 per 1,000 Liters).
```

---

### 2.3 Acoustic Hydrophone Cavitation Audio & Oscilloscope Prompt
**Component Built:** [`app/audio_diagnostic.py`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app/audio_diagnostic.py) & Web Audio API Visualizer

```text
Implement an industrial acoustic hydrophone telemetry synthesizer and real-time visualizer:

1. Backend Profile Generator:
   - For nominal fixtures: 420 Hz fundamental sine wave, 2.1% THD (Laminar Full Flush).
   - For diaphragm tear leaks: 2,420 Hz turbulent screech, 14.5 Hz flutter, 38.4% THD (Cavitation).
   - For solenoid phantom cycling: 120 Hz electrical latch hum, square wave harmonics.
   - For quiescent baseline: 0 Hz electronic sensor thermal noise floor.

2. Frontend Web Audio API & Canvas Oscilloscope:
   - Create browser AudioContext with OscillatorNode, GainNode, and LFO flutter modulation.
   - Render a real-time oscilloscope canvas (480x90) with subtle reticle grid and center baseline.
   - Dynamically transition wave color from cyan (#00A3E0) to warning red (#FF4D5A) upon cavitation screech.
```

---

### 2.4 Interactive Kohler K-10673 CAD Exploded Schematics Prompt
**Component Built:** Vector SVG CAD Component in [`ui/index.html`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/ui/index.html) & [`ui/app.js`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/ui/app.js)

```text
Create an architectural vector SVG exploded diagram modeling the Kohler K-10673 Tripoint Flushometer:

Components to render:
1. Solid Brass Valve Body Casting (K-10673-BODY)
2. Tripoint EPDM Molded Diaphragm Assembly with bypass filter (GP1138930)
3. 24V DC Bi-Stable Pulse Solenoid Actuator (10673-SOL)
4. Dynamic Supply Pressure Cartridge & Regulator (GP1044432)
5. Infrared Optical Sensor Eye Module (K-13688)

Interactive Behavior:
- Connect exploded parts with dashed CAD dimension lines.
- When an incident is active, inspect root_cause and apply CSS keyframe glow animation (.schematic-fault-active)
  to pulse the exact faulty mechanical component in red.
- Clicking any part opens an engineering spec callout displaying part number, price, and depot shelf location.
```

---

### 2.5 Multi-Airport Fleet Portfolio & National Benchmarking Prompt
**Component Built:** [`app/portfolio.py`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app/portfolio.py)

```text
Create a multi-airport fleet aggregation engine for aviation facility directors:

Airports to model:
1. Pune International Airport (PNQ): Live Digital Twin, 97 fixtures, 28,400 daily pax, ₹443k/mo saved.
2. Mumbai Chhatrapati Shivaji T2 (BOM): Synthetic Fleet Twin, 184 fixtures, 74,000 daily pax, ₹1.25M/mo saved.
3. Delhi Indira Gandhi T3 (DEL): Synthetic Fleet Twin, 312 fixtures, 142,000 daily pax, ₹1.83M/mo saved.

Outputs:
- Consolidated national metrics: 593 fixtures, 260,900 L/day conserved, ₹3.52M/month in tariff avoidance.
- Header dropdown switcher enabling instant context switching between airports.
- Benchmark dialog displaying national sustainability ranking table and composite facility health comparison.
```

---

### 2.6 Scope 2/3 GHG Carbon Nexus & LEED Scorecard Prompt
**Component Built:** [`app/esg.py`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app/esg.py)

```text
Implement an institutional ESG water-energy nexus and green building rating engine:

Constants (Central Electricity Authority CEA India Database):
- Municipal water pumping energy intensity: 1.82 kWh per 1,000 Liters (kL).
- CEA Grid emission factor: 0.82 kg CO2e per kWh -> 1.4924 kg CO2e per kL avoided.
- Tree absorption: 21.8 kg CO2 per tree-year.
- Tanker truck capacity: 12,000 Liters.

LEED v4.1 Operations & Maintenance Scorecard:
- WE Prerequisite 1: Indoor Water Use Reduction (20% Baseline) -> Compliant (>45% achieved).
- WE Credit 1: Indoor Water Efficiency -> 5/6 Points.
- WE Credit 2: Water Sub-metering & AI Monitoring -> 2/2 Points.
- EA Credit 1: Pumping Energy Reduction -> 4/5 Points.
- Output: Composite Score 92/100 (LEED Platinum Ready).
- Generate verifiable digital certificate with cryptographic SHA-256 validation seal.
```

---

### 2.7 IBM Maximo & SAP PM CMMS Work Order Generator Prompt
**Component Built:** Maximo Gateway in [`app/esg.py`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app/esg.py) & Dialog in UI

```text
Build an industrial Computerized Maintenance Management System (CMMS) work order generator
compatible with IBM Maximo Asset Management (v7.6.1) and SAP Plant Maintenance (PM).

Fields:
- Work Order Number: WO-2026-XXXXX
- Asset Tag: KOHLER-{device_id}
- Functional Location: PNQ-T2-R14-STALL-03
- Failure Code: CONTINUOUS_LEAK
- Safety Mandate: Level 2 Domestic Water System Lockout/Tagout (LOTO)
- Required Spare: Kohler OEM part number, price, and reserved storage location
- Job Plan: 8 numbered sequential steps (isolate stopcock, remove flange, replace diaphragm, torque 18 Nm, verify flow)
- Aviation barcode scan code & technician digital signature block
- 1-click printable job card modal.
```

---

### 2.8 Weibull Asset Lifecycle Hazard Rate Modeler Prompt
**Component Built:** [`app/lifecycle.py`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app/lifecycle.py)

```text
Formulate an asset lifecycle degradation and predictive maintenance model for solenoid flushometers:

1. Cycle Wear Metric: Completed actuations vs 500,000 rated cycle lifetime.
2. Weibull Hazard Rate Formulation:
   - Shape parameter beta = 2.8 (mechanical wear-out regime), scale parameter eta = 500,000 cycles.
   - Cumulative failure risk: R(t) = 1 - exp(-((cycles + delta_7d) / eta)^beta).
3. Vibration Chatter Index (0 to 100): Quantify armature micro-bounce and water hammer transient spikes.
4. Output: Fleet degradation overview ranking top-5 at-risk assets with recommended preventive intervention.
```

---

### 2.9 Multimodal Passenger QR Feedback Ingestion & Fusion Prompt
**Component Built:** [`app/feedback.py`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/app/feedback.py)

```text
Design a traveler mobile feedback ingestion engine that boosts physical sensor confidence:

1. API Endpoint: POST /api/feedback accepting restroom_id, issue_category, stall_number, and optional comment.
2. Multimodal Matching Logic:
   - Match reported restroom and stall to active device in digital twin.
   - If device has an open anomaly alert, apply a +15% Bayesian fusion boost to leak confidence (capped at 0.99).
   - If priority was P2, escalate to P1 due to traveler visibility and public brand impact.
3. Return confirmation payload showing elevated confidence and matched device ID.
```

---

### 2.10 Industrial High-Contrast Dark-Theme Ops Center UI Prompt
**Component Built:** [`ui/style.css`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/ui/style.css) & [`ui/index.html`](file:///c:/Users/sahak/OneDrive/Documents/AIDS/Personal/Kohler/kohler-aquaguard-ai/ui/index.html)

```text
Redesign the AquaGuard frontend into a research-grade commercial facility command center.

Visual Language:
- Palette: Dark control-room theme (Background #080B10, Panels #10151C, Borders #202833).
- Primary Text: #F4F7FA; Muted Text: #8B96A5; Kohler Accent: #00A3E0.
- State Colors: Normal #35D07F, Warning #F5B942, Critical #FF4D5A.
- Layout: Spatial Facility Twin Map, Terminal Status Cards, 24-Hour Diurnal Timeline Canvas,
  Dedicated Incident Workspace with OEM spare cards, CAD schematics, and closed-loop verification stepper.
- Responsive, zero npm build step, pure ES6 HTML/CSS/JS served directly via FastAPI.
```

---

## Part 3: Custom Specialized AI Prompts Designed for Facility Operations

These custom prompts are pre-configured operational templates designed for airport facility managers, sustainability directors, and plumbing supervisors:

### 3.1 Automated Shift-Handoff Facility Intelligence Briefing Prompt
**Trigger:** Facility supervisor shift change (06:00, 14:00, 22:00 IST).

```text
[CONTEXT INJECTION: Facility Health Hierarchy, Open Incidents, Resolved Ledger, Spares Depletion]

You are AquaGuard AI. Compose an executive Shift-Handoff Briefing for the incoming Terminal Facilities Lead.

Include:
1. Executive Summary: 1-sentence composite health rating and open P1/P2 count.
2. Active Critical Incidents: Device ID, location, root cause, assigned technician, and SLA minutes remaining.
3. Closed-Loop Achievements: Water volume banked to ledger during the outgoing shift and commercial savings.
4. OEM Spares Advisory: Depot parts with inventory <= 3 units requiring procurement requisition.
5. High-Risk Assets: Top 2 fixtures exhibiting > 70% Weibull 7-day failure probability.

Tone: Crisp, military-grade operational brevity. Use markdown bullet points with bold metrics.
```

---

### 3.2 Municipal Water Tariff Stress-Testing & ROI Prompt
**Trigger:** Utility budget review or municipal water tariff revision announcement.

```text
[CONTEXT INJECTION: Annual Water Consumption Baseline, Current Tariff ₹48.50/kL, Fleet Fixture Count 97]

Given a projected {{tariff_hike_pct}}% municipal commercial tariff escalation and a {{pax_growth_pct}}%
increase in passenger footfall over the next 12 months:

Calculate and report:
1. Unmitigated Financial Exposure: Total expenditure if baseline leak rate persists without AquaGuard AI.
2. Projected Conservation Volume: Liters saved under 100% smart sensor coverage.
3. Avoided Operational Expenditure: Net rupee savings at the elevated tariff schedule.
4. Capital Payback Horizon: Exact months required to amortize smart sensor retrofit costs (₹6,500/fixture).
5. 5-Year Cumulative Net ROI: Long-term capital dividend.
```

---

### 3.3 Contractor SLA Breach Enforcement & Escalation Prompt
**Trigger:** Technician SLA timer drops below 3 minutes without on-site arrival verification.

```text
[CONTEXT INJECTION: Incident ID, Device ID, Zone, Assigned Technician, Current SLA Remaining Seconds]

The SLA countdown for incident {{incident_id}} on fixture {{device_id}} has reached {{sla_seconds}} seconds.
Generate an automated emergency CAD dispatch escalation payload:

1. Broadcast high-priority SMS/WhatsApp alert to Plumbing Supervisor:
   "URGENT: P1 SLA Breach Imminent on {{device_id}} ({{zone}}). Unmitigated loss: {{flow_lpm}} L/min.
   Technician {{tech_name}} has not verified arrival. Backup specialist required immediately."
2. Log breach warning to official compliance audit log with ISO timestamp.
3. Surface priority dispatch banner in AI Command Center dashboard.
```
