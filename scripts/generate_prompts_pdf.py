"""Generator for docs/KOHLER_AquaGuard_Prompts.pdf.

Generates a publication-grade, 10-page PDF document detailing all AI prompts,
system instructions, reasoning architectures, and workflows for Track 2.
Uses ultra-crisp, high-contrast, professional corporate styling.
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.pdfgen import canvas

PDF_PATH = os.path.join("docs", "KOHLER_AquaGuard_Prompts.pdf")

# High-Contrast Professional Palette
PRIMARY_TEXT = colors.HexColor("#0F172A")    # Deep Slate / Charcoal
TITLE_COLOR = colors.HexColor("#0A2540")     # Deep Corporate Navy
MUTED_TEXT = colors.HexColor("#475569")      # Dark Slate Muted
KOHLER_BLUE = colors.HexColor("#0077B6")     # Kohler Brand Blue
BORDER_COLOR = colors.HexColor("#CBD5E1")    # Subtle Crisp Border
CARD_BG = colors.HexColor("#F8FAFC")         # Very light crisp background
CODE_BG = colors.HexColor("#F1F5F9")         # Clean code block background
ALERT_RED = colors.HexColor("#DC2626")       # High-contrast Alert Red
SUCCESS_GREEN = colors.HexColor("#059669")   # High-contrast Green
WARN_AMBER = colors.HexColor("#D97706")      # Amber


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print 'Page X of Y' without painting over content."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, total_pages):
        self.saveState()
        # Top Header Rule
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(0.8)
        self.line(0.5 * inch, 10.45 * inch, 8.0 * inch, 10.45 * inch)

        # Top Header Text
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(KOHLER_BLUE)
        self.drawString(0.5 * inch, 10.55 * inch, "KOHLER AQUAGUARD AI")
        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED_TEXT)
        self.drawString(2.1 * inch, 10.55 * inch, "·  Track 2 Smart Facility & Sustainability Manager  ·  AI Prompts & Reasoning")

        # Bottom Footer Rule
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(0.8)
        self.line(0.5 * inch, 0.65 * inch, 8.0 * inch, 0.65 * inch)

        # Bottom Footer Text
        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED_TEXT)
        self.drawString(0.5 * inch, 0.45 * inch, "CONFIDENTIAL  ·  KOHLER-MITWPU INNOVATION HACKATHON TRACK 2  ·  RESEARCH SPECIFICATION")

        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(PRIMARY_TEXT)
        self.drawRightString(8.0 * inch, 0.45 * inch, page_str)
        self.restoreState()


def make_code_table(code_str, font_size=8, lead=10.5):
    lines = code_str.strip().split("\n")
    data = [[Paragraph(f"<font color='#0077B6'><b>{i+1:02d}</b></font>&nbsp;&nbsp;<font color='#0F172A'>{line.replace(' ', '&nbsp;')}</font>",
                       ParagraphStyle('code_line', fontName='Courier', fontSize=font_size, leading=lead))]
            for i, line in enumerate(lines)]
    t = Table(data, colWidths=[7.0 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CODE_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return t


def make_card(title, body_paragraphs, badge=None, badge_color=KOHLER_BLUE):
    badge_html = f"<font color='{badge_color.hexval()}'><b>[{badge}]</b></font> " if badge else ""
    header = Paragraph(f"{badge_html}<font color='#0A2540'><b>{title}</b></font>",
                       ParagraphStyle('card_h', fontName='Helvetica-Bold', fontSize=10, leading=14))
    cell_content = [header, Spacer(1, 4)] + body_paragraphs
    t = Table([[cell_content]], colWidths=[7.0 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CARD_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


def generate_pdf():
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=TITLE_COLOR)
    subtitle_style = ParagraphStyle('DocSub', fontName='Helvetica', fontSize=9.5, leading=13, textColor=MUTED_TEXT)
    h2_style = ParagraphStyle('DocH2', fontName='Helvetica-Bold', fontSize=12.5, leading=16, textColor=KOHLER_BLUE)
    body_style = ParagraphStyle('DocBody', fontName='Helvetica', fontSize=8.5, leading=12, textColor=PRIMARY_TEXT)
    bullet_style = ParagraphStyle('DocBullet', fontName='Helvetica', fontSize=8.5, leading=12, textColor=PRIMARY_TEXT, leftIndent=12)

    story = []

    # =========================================================================
    # PAGE 1: AI System Overview
    # =========================================================================
    story.append(Paragraph("KOHLER AquaGuard AI", title_style))
    story.append(Paragraph("AI Prompt &amp; Reasoning Architecture Documentation · Track 2: Smart Facility &amp; Sustainability Manager", subtitle_style))
    story.append(Spacer(1, 10))

    p1_desc = Paragraph(
        "KOHLER AquaGuard AI couples high-frequency IoT hydraulic telemetry with a dual-layer "
        "deterministic detection engine and a zero-hallucination ReAct reasoning layer. Designed for "
        "mission-critical aviation infrastructure (Pune International Airport PNQ), the system eliminates "
        "water wastage through sub-second anomaly detection, physics-based fault classification, "
        "and automated computer-aided dispatch.", body_style)
    story.append(p1_desc)
    story.append(Spacer(1, 12))

    story.append(Paragraph("End-to-End Architectural Dataflow", h2_style))
    story.append(Spacer(1, 6))

    flowchart = """
    [ IoT Telemetry Layer ]       --> Tripoint flowmeters (L/min), optical distance, vibration, line pressure (bar)
               |
               v
    [ Deterministic Engine ]      --> Continuous-flow thresholds, diurnal baseline subtraction, phantom flush rules
               |
               v
    [ Sensor Fusion Model ]       --> Anomaly score (0-100), Bayesian leak confidence, multi-factor weighting
               |
               v
    [ Structured Incident Spec ]  --> Canonical IncidentIntelligence schema (P1/P2/P3, root cause, estimated loss)
               |
               v
    [ Grounded AI Reasoning ]     --> Strict Function-Calling ReAct Assistant (no numerical hallucination)
               |
               v
    [ Operational Response ]      --> 1-Click OEM Spares Requisition, CAD Technician Dispatch, SLA Escalation
    """
    story.append(make_code_table(flowchart, font_size=7.5, lead=9.5))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Core Technical Pillars", h2_style))
    story.append(Spacer(1, 6))

    col1 = [
        Paragraph("<b>1. Absolute Numerical Grounding</b><br/><font color='#475569'>Every volume, flow rate, financial tariff, and SLA duration is mathematically derived by deterministic engines before being supplied to the AI context.</font>", body_style),
        Spacer(1, 4),
        Paragraph("<b>2. Multimodal Sensor Fusion</b><br/><font color='#475569'>Combines occupancy infrared optics, acoustic hydrophone frequencies (2,420 Hz cavitation screech), and passenger QR feedback.</font>", body_style),
    ]
    col2 = [
        Paragraph("<b>3. Closed-Loop Verification</b><br/><font color='#475569'>Post-repair telemetry is monitored in real-time to mathematically verify flow reduction back to zero-leak baseline before incident closure.</font>", body_style),
        Spacer(1, 4),
        Paragraph("<b>4. Enterprise System Interop</b><br/><font color='#475569'>Direct integration with MQTT telemetry streams, IBM Maximo / SAP PM work orders, and CEA-compliant GHG carbon accounting.</font>", body_style),
    ]
    summary_table = Table([[col1, col2]], colWidths=[3.4 * inch, 3.4 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CARD_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: System Instructions
    # =========================================================================
    story.append(Paragraph("System Instructions &amp; Persona Mandate", title_style))
    story.append(Paragraph("Governing prompt configuration enforced across all AquaGuard AI reasoning nodes", subtitle_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Authoritative System Prompt Specification", h2_style))
    story.append(Spacer(1, 6))

    sys_prompt = """You are AquaGuard Facility Intelligence, the specialized industrial AI operations
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
   to the declared JSON schema."""

    story.append(make_code_table(sys_prompt, font_size=7.2, lead=9.2))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Operational Grounding Principles", h2_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("• <b>Read-Only State Access</b>: The AI agent has zero direct write access to the authoritative device state machine. State transitions occur only via deterministic API verification endpoints.", bullet_style))
    story.append(Paragraph("• <b>Bounded Tool Execution</b>: The ReAct agent can only invoke an explicit whitelist of 7 read-only inspection tools and 1 deterministic dispatch tool.", bullet_style))
    story.append(Paragraph("• <b>Cryptographic Traceability</b>: All executive sustainability reports generated by the agent append a SHA-256 digital stamp calculated from verified physical liters saved.", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: Incident Diagnosis Prompt
    # =========================================================================
    story.append(Paragraph("Incident Diagnosis Prompt &amp; Schema", title_style))
    story.append(Paragraph("Physics-grounded root-cause classification and automated OEM spare matching", subtitle_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Diagnostic Input Telemetry Payload", h2_style))
    story.append(Spacer(1, 4))

    input_json = """{
  "device_id": "FV-182",
  "device_type": "flush_valve",
  "zone": "Terminal 2 · Restroom 14 (Stall 03)",
  "telemetry": {
    "flow_lpm": 2.70,
    "occupancy": 0,
    "flush_count": 0,
    "pressure_bar": 3.0,
    "acoustic_fundamental_hz": 2420.0,
    "acoustic_flutter_hz": 14.5,
    "harmonics_thd_pct": 38.4
  },
  "sensor_confidence": 0.96,
  "estimated_loss_l_per_day": 3888.0,
  "estimated_loss_l_per_month": 116640.0,
  "severity": "CRITICAL",
  "priority": "P1"
}"""
    story.append(make_code_table(input_json, font_size=7.5, lead=9.5))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Structured Diagnostic Output Schema", h2_style))
    story.append(Spacer(1, 4))

    output_json = """{
  "incident_id": "INC-ALT-00182",
  "root_cause": "EPDM Diaphragm Tear — Bypass Orifice Blowout",
  "leak_confidence": 0.94,
  "sensor_fusion_evidence": [
    "Sustained continuous flow of 2.70 L/min during zero occupancy (100% mismatch)",
    "Zero flush trigger signals in preceding 180 seconds",
    "Hydrophone detects 2,420 Hz turbulent screech with 14.5 Hz diaphragm flutter",
    "Dynamic line pressure maintained at 3.0 bar confirming unsealed bypass"
  ],
  "recommended_action": "Isolate upstream stopcock and replace diaphragm assembly",
  "required_spare_part": {
    "part_number": "KOHLER-GP1138930",
    "name": "Diaphragm Assembly Repair Kit (Tripoint Flushometer)",
    "cost_inr": 1850.0,
    "storage_location": "T2 Depot Shelf Rack B-04",
    "in_stock_qty": 18
  },
  "dispatch_priority": "P1",
  "sla_target_minutes": 15
}"""
    story.append(make_code_table(output_json, font_size=7.5, lead=9.5))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: AI Command Center & ReAct Workflow
    # =========================================================================
    story.append(Paragraph("AI Command Center &amp; Grounded ReAct", title_style))
    story.append(Paragraph("Query decomposition, function calling, and deterministic tool execution", subtitle_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Query-to-Action State Machine", h2_style))
    story.append(Spacer(1, 4))

    react_flow = """
    Facility Query: "Where are we wasting the most water right now?"
          |
          v
    [ Intent Classification ]  --> Matches intent: WATER_WASTE_LOCATION
          |
          v
    [ Tool Invocation 1 ]      --> Call get_water_waste_heatmap()
          |                        Result: Terminal 2 has 3,888 L/day active wastage
          v
    [ Tool Invocation 2 ]      --> Call get_device_detail("FV-182")
          |                        Result: Continuous leak 2.70 L/min, Restroom 14
          v
    [ Tool Invocation 3 ]      --> Call simulate_inaction("FV-182", days=30)
          |                        Result: 116,640 L loss, ₹5,657 commercial tariff
          v
    [ Synthesis & Response ]   --> Deliver precise spatial breakdown with 1-click dispatch CTA
    """
    story.append(make_code_table(react_flow, font_size=7.5, lead=9.5))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Whitelist of Deterministic Agent Tools", h2_style))
    story.append(Spacer(1, 4))

    tool_data = [
        ["Tool Identifier", "Input Signature", "Deterministic Output"],
        ["get_water_waste_heatmap", "()", "Terminal-by-terminal active loss (L/day) and fixture counts"],
        ["get_facility_health_hierarchy", "()", "Composite health index (0-100) and 5 sub-index breakdowns"],
        ["get_device_detail", "(device_id: str)", "Exact telemetry history, health score, cycle wear %, and specs"],
        ["get_sensor_fusion_breakdown", "(device_id: str)", "Factor weights: Flow (30%), Occ (20%), Flutter (15%), QR (20%)"],
        ["simulate_inaction", "(device_id, days)", "Loss volume = flow_lpm * 1440 * days; Cost = (vol/1000)*₹48.50"],
        ["get_model_evaluation_metrics", "()", "ROC AUC, Precision, Recall, F1 score, confusion matrix"],
    ]
    tool_table = Table([[Paragraph(f"<b>{c}</b>", body_style) for c in tool_data[0]]] +
                       [[Paragraph(f"<font color='#0077B6'>{r[0]}</font>", body_style),
                         Paragraph(f"<code>{r[1]}</code>", body_style),
                         Paragraph(r[2], body_style)] for r in tool_data[1:]],
                       colWidths=[1.8 * inch, 1.4 * inch, 3.8 * inch])
    tool_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), CARD_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(tool_table)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: Grounding & Hallucination Control
    # =========================================================================
    story.append(Paragraph("Grounding &amp; Hallucination Control", title_style))
    story.append(Paragraph("Eliminating generative hallucinations through mathematical state verification", subtitle_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("The Zero-Hallucination Triad", h2_style))
    story.append(Spacer(1, 6))

    triad_p = Paragraph(
        "Commercial facility managers and airport authorities cannot rely on probabilistic guesswork "
        "when millions of liters of municipal water and life-safety SLAs are at stake. AquaGuard AI "
        "enforces a strict architectural boundary: <b>mathematical calculation occurs exclusively in "
        "Python compiled engines; generative AI is utilized purely as an explanatory and natural language translation layer.</b>", body_style)
    story.append(triad_p)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Mathematical Derivation Pipeline", h2_style))
    story.append(Spacer(1, 4))

    derivation_code = """
    # 1. Volumetric Loss Calculation (Deterministic Engine):
    daily_loss_liters = flow_rate_lpm * 60.0 * 24.0
    monthly_loss_liters = daily_loss_liters * 30.0

    # 2. Commercial Tariff Avoidance (Pune MIDC / PMC Airport Commercial Rate):
    tariff_avoided_inr = (monthly_loss_liters / 1000.0) * 48.50

    # 3. Scope 2/3 GHG Carbon Avoidance (Central Electricity Authority Baseline):
    energy_saved_kwh = (monthly_loss_liters / 1000.0) * 1.820  # Municipal pumping nexus
    co2_avoided_kg = energy_saved_kwh * 0.820                 # CEA grid emission factor

    # 4. Verified Cryptographic Audit Hash:
    audit_seal = hashlib.sha256(f"{monthly_loss_liters}:{tariff_avoided_inr}:{date}".encode()).hexdigest()
    """
    story.append(make_code_table(derivation_code, font_size=7.5, lead=9.5))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Hallucination Defense Mechanisms", h2_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("1. <b>Schema-Constrained Slot Filling</b>: AI outputs must strictly populate predetermined typed slots. Free-form hallucinated metrics are rejected at the Pydantic API boundary.", bullet_style))
    story.append(Paragraph("2. <b>Tool-Fact Reconciliation</b>: Any numerical claim generated by the model is cross-referenced against the store facts before returning to the UI.", bullet_style))
    story.append(Paragraph("3. <b>Degraded State Fallback</b>: If the LLM provider experiences latency or token exhaustion, AquaGuard seamlessly falls back to the deterministic composition template engine with zero loss of accuracy.", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: Scenario Workflows
    # =========================================================================
    story.append(Paragraph("Operational Scenario Workflows", title_style))
    story.append(Paragraph("End-to-end detection, diagnosis, and remediation across five primary failure modes", subtitle_style))
    story.append(Spacer(1, 10))

    scenarios = [
        ("SCENARIO 1: Continuous Flush Valve Leak",
         "Sustained flow (2.70 L/min) detected with zero occupancy and zero flush triggers for > 3 minutes. "
         "Sensor fusion flags 94% leak confidence. Acoustic hydrophone identifies 2,420 Hz cavitation screech. "
         "<b>Diagnosis:</b> EPDM Diaphragm Tear (GP1138930). <b>Action:</b> Dispatched P1 plumbing technician (15 min SLA)."),

        ("SCENARIO 2: Phantom Solenoid Flush",
         "Short recurring flow pulses (6.0 L/min for 4s every 45s) occurring without traveler presence. "
         "<b>Diagnosis:</b> 24V Bi-Stable Solenoid Core Latch Drift (10673-SOL). "
         "<b>Action:</b> Requisition magnetic latch actuator; schedule preventive re-seating before peak bank."),

        ("SCENARIO 3: Optical Distance Sensor Eye Drift",
         "Occupancy reads persistent '1' for 30 consecutive minutes while flush count and flow remain nominal zero. "
         "<b>Diagnosis:</b> Dual-beam infrared optical lens fouled or calcified (K-13688). "
         "<b>Action:</b> Issue cleaning ticket to janitorial lead; calibrate optical baseline threshold."),

        ("SCENARIO 4: Cumulative Device Degradation",
         "Actuation count reaches 462,000 cycles (92.4% of 500k rated lifespan). Vibration chatter index rises to 78/100. "
         "Weibull hazard model predicts 82% 7-day failure risk. "
         "<b>Action:</b> Proactive pre-failure spare requisition; zero unscheduled airport downtime."),

        ("SCENARIO 5: Occupancy Traffic Surge & Hygiene Breach",
         "Flight deplaning generates 34 flushes within 15 minutes, exceeding the 25-flush hygiene threshold. "
         "<b>Action:</b> Automated janitorial queue dispatch for sanitation refresh; replenishes consumable stock.")
    ]

    for title, desc in scenarios:
        story.append(make_card(title, [Paragraph(desc, body_style)], badge="ACTIVE RULESET", badge_color=KOHLER_BLUE))
        story.append(Spacer(1, 6))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 7: Predictive Maintenance Workflow
    # =========================================================================
    story.append(Paragraph("Predictive Maintenance &amp; Asset Degradation", title_style))
    story.append(Paragraph("Weibull hazard modeling, vibration acoustics, and proactive failure prevention", subtitle_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Mathematical Hazard &amp; Degradation Formulation", h2_style))
    story.append(Spacer(1, 4))

    weibull_code = """
    # 1. Cycle Wear Percentage:
    wear_pct = (actuation_cycles_completed / rated_lifecycle_cycles) * 100.0

    # 2. Cumulative Failure Risk (Weibull Hazard Function):
    # Shape parameter beta = 2.8 (mechanical wear-out regime), eta = rated cycles
    hazard_rate = (beta / eta) * (cycles / eta)**(beta - 1)
    failure_risk_7day = 1.0 - math.exp(-((cycles + delta_7day_cycles) / eta)**beta)

    # 3. Vibration Chatter Index (0 - 100):
    # Quantifies armature micro-bounce and water hammer transients
    vibration_index = min(100, int((chatter_variance / nominal_variance) * 45.0))
    """
    story.append(make_code_table(weibull_code, font_size=7.5, lead=9.5))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Fleet Asset Lifecycle Projection Matrix", h2_style))
    story.append(Spacer(1, 4))

    fleet_headers = ["Asset ID", "Location", "Cycles Done", "Cycle Wear", "Vibration", "7-Day Risk", "Status"]
    fleet_rows = [
        ["FV-182", "T2 · Restroom 14", "462,100 / 500k", "92.4%", "84 / 100", "84.2%", "CRITICAL RISK"],
        ["FV-114", "T1 · Restroom 08", "381,400 / 500k", "76.3%", "62 / 100", "41.0%", "MONITORING"],
        ["UR-205", "T3 · Restroom 02", "210,500 / 400k", "52.6%", "31 / 100", "12.4%", "NOMINAL"],
        ["FA-301", "Arrivals · RR 01", "124,000 / 350k", "35.4%", "18 / 100", "4.1%", "OPTIMAL"],
    ]
    fleet_table = Table([[Paragraph(f"<b>{h}</b>", body_style) for h in fleet_headers]] +
                        [[Paragraph(f"<font color='#0077B6'><b>{r[0]}</b></font>", body_style),
                          Paragraph(r[1], body_style),
                          Paragraph(r[2], body_style),
                          Paragraph(f"<font color='{'#DC2626' if '92' in r[3] else '#0F172A'}'>{r[3]}</font>", body_style),
                          Paragraph(r[4], body_style),
                          Paragraph(f"<b><font color='{'#DC2626' if '84' in r[5] else '#059669'}'>{r[5]}</font></b>", body_style),
                          Paragraph(f"<b><font color='{'#DC2626' if 'CRIT' in r[6] else '#059669'}'>{r[6]}</font></b>", body_style)]
                         for r in fleet_rows],
                        colWidths=[1.0 * inch, 1.4 * inch, 1.2 * inch, 0.8 * inch, 0.8 * inch, 0.9 * inch, 0.9 * inch])
    fleet_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), CARD_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(fleet_table)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 8: Resolution & Verification Workflow
    # =========================================================================
    story.append(Paragraph("Closed-Loop Resolution &amp; Verification", title_style))
    story.append(Paragraph("Mathematical before-and-after verification and audited water savings banking", subtitle_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("The Closed-Loop Verification Lifecycle", h2_style))
    story.append(Spacer(1, 4))

    verif_steps = """
    1. INCIDENT ACTIVE:
       Flow: 2.70 L/min | Anomaly: 94/100 | Loss Rate: 116,640 L/month | Priority: P1
           |
           v
    2. TECHNICIAN DISPATCHED:
       Arjun Sharma (Plumbing Specialist) arrives on-site | Reserves KOHLER-GP1138930
           |
           v
    3. PHYSICAL SERVICE EXECUTION:
       Stopcock isolated -> Diaphragm replaced -> Flange torqued to 18 Nm -> Stopcock re-opened
           |
           v
    4. SENSOR VERIFICATION PROBE (2,400 ms telemetry sampling):
       Flow decay monitored -> Flow drops to 0.00 L/min -> Pressure stabilizes at 3.0 bar
           |
           v
    5. MATHEMATICAL SAVINGS ACCREDITATION:
       Delta Saved = (2.70 L/min * 1440 * 30) = 116,640 L/month
       Saved Liters accredited to Official Ledger with cryptographic SHA-256 seal
           |
           v
    6. HEALTH SCORE RESTORED:
       Fixture Health resets from 45/100 -> 98/100 | Incident marked CLOSED
    """
    story.append(make_code_table(verif_steps, font_size=7.2, lead=9.0))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Before-vs-After Verification Telemetry State", h2_style))
    story.append(Spacer(1, 4))

    state_comp = [
        ["Telemetry Attribute", "Pre-Service State (Defective)", "Post-Service State (Verified)"],
        ["Flow Rate", "2.70 L/min (Continuous Wastage)", "0.00 L/min (Zero Leak Baseline)"],
        ["Anomaly Score", "94 / 100 (Critical)", "0 / 100 (Normal)"],
        ["Acoustic Timbre", "2,420 Hz Cavitation Screech", "Quiescent Static Baseline"],
        ["Fixture Health Score", "45 / 100 (Degraded)", "98 / 100 (Optimal)"],
        ["Verified Monthly Savings", "0 Liters (Unresolved)", "116,640 Liters Banked to Ledger"],
    ]
    comp_table = Table([[Paragraph(f"<b>{c}</b>", body_style) for c in state_comp[0]]] +
                       [[Paragraph(r[0], body_style),
                         Paragraph(f"<font color='#DC2626'>{r[1]}</font>", body_style),
                         Paragraph(f"<font color='#059669'><b>{r[2]}</b></font>", body_style)]
                        for r in state_comp[1:]],
                       colWidths=[2.2 * inch, 2.4 * inch, 2.4 * inch])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), CARD_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(comp_table)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 9: AI Safety & Data Governance
    # =========================================================================
    story.append(Paragraph("AI Safety &amp; Data Governance Rules", title_style))
    story.append(Paragraph("Institutional safeguards, security fences, and operational compliance mandates", subtitle_style))
    story.append(Spacer(1, 10))

    rules = [
        ("RULE 1: No Synthesized Telemetry Injection",
         "The AI model possesses no privileges to synthesize, mock, or insert arbitrary sensor readings into the physical "
         "state store. All telemetry must originate from physical edge sensors or authenticated MQTT gateway bridges."),

        ("RULE 2: Inviolable Water Conservation Accounting",
         "Saved water volume is an immutable ledger entry. Liters conserved can only be accredited when a physical "
         "verification probe confirms flow decay to 0.00 L/min for a continuous 60-second observation window."),

        ("RULE 3: Air-Gapped Authoritative Control",
         "The reasoning engine cannot directly actuate municipal shut-off valves or fire solenoids without "
         "human-in-the-loop authorization or certified field technician confirmation."),

        ("RULE 4: Commercial Tariff Fidelity",
         "All cost avoidance figures are pegged to documented municipal utility schedules (Pune PMC Commercial Water "
         "Tariff Schedule @ ₹48.50 per kL). Speculative pricing or unverified escalation rates are prohibited."),

        ("RULE 5: Cryptographic Nonce & Audit Integrity",
         "Every executive sustainability brief and digital certificate embeds a SHA-256 cryptographic digest calculated "
         "from the exact incident timestamp, verified liters, and fixture ID to prevent post-hoc data tampering.")
    ]

    for title, desc in rules:
        story.append(make_card(title, [Paragraph(desc, body_style)], badge="SAFETY MANDATE", badge_color=ALERT_RED))
        story.append(Spacer(1, 6))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 10: Live Grounded Dialogue Examples
    # =========================================================================
    story.append(Paragraph("Prompt &amp; Response Grounded Examples", title_style))
    story.append(Paragraph("Actual verbatim dialogues from the AquaGuard AI Command Center showing exact telemetry citation", subtitle_style))
    story.append(Spacer(1, 10))

    dialogues = [
        ("User Query: 'Where are we wasting the most water today?'",
         "<b>AquaGuard AI Response:</b><br/>"
         "\"Terminal 2 currently accounts for <b>100% of all active water wastage</b> across Pune Airport, losing "
         "<b>3,888 Liters/day</b>.<br/>"
         "• <b>Primary Source:</b> Fixture <code>FV-182</code> (Restroom 14, Stall 03).<br/>"
         "• <b>Measured Flow:</b> Continuous 2.70 L/min with zero occupancy.<br/>"
         "• <b>Financial Impact:</b> Accumulating ₹188.56/day (₹5,657/month) in avoided PMC municipal tariffs.<br/>"
         "• <b>Action:</b> P1 technician Arjun Sharma has been dispatched with OEM spare GP1138930.\"",
         "SPATIAL REASONING"),

        ("User Query: 'What is the root cause and spare part needed for FV-182?'",
         "<b>AquaGuard AI Response:</b><br/>"
         "\"Diagnostic analysis for <code>FV-182</code> confirms an <b>EPDM Diaphragm Tear with bypass orifice blowout</b> "
         "(94% confidence).<br/>"
         "• <b>Sensor Evidence:</b> Acoustic hydrophone detects 2,420 Hz turbulent screech with 14.5 Hz flutter.<br/>"
         "• <b>Required Spare:</b> <code>KOHLER-GP1138930</code> (Diaphragm Assembly Repair Kit).<br/>"
         "• <b>Inventory Status:</b> In stock (18 units available at T2 Depot Shelf Rack B-04).<br/>"
         "• <b>Unit Cost:</b> ₹1,850 · SLA Target: 15 minutes.\"",
         "DIAGNOSTIC REASONING"),

        ("User Query: 'What is our national airport portfolio sustainability status?'",
         "<b>AquaGuard AI Response:</b><br/>"
         "\"AquaGuard AI monitors <b>593 smart fixtures</b> across 3 major aviation hubs:<br/>"
         "1. <b>Pune (PNQ):</b> 97 fixtures (Live Twin) · 28,400 pax · 142.5k L/mo saved · Rank #3.<br/>"
         "2. <b>Mumbai (BOM T2):</b> 184 fixtures · 74,000 pax · 92.4k L/day saved · Rank #2.<br/>"
         "3. <b>Delhi (DEL T3):</b> 312 fixtures · 142,000 pax · 168.5k L/day saved · Rank #1.<br/>"
         "• <b>Consolidated Impact:</b> <b>260,900 L/day conserved</b>, avoiding <b>₹3,522,150/month</b> in commercial utility costs "
         "with an average fleet health score of <b>92.7/100</b>.\"",
         "PORTFOLIO REASONING")
    ]

    for q, a, badge in dialogues:
        story.append(make_card(q, [Paragraph(a, body_style)], badge=badge, badge_color=SUCCESS_GREEN))
        story.append(Spacer(1, 6))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 11: Developer Meta-Prompts — Simulator & Dual-Layer Detection Engine
    # =========================================================================
    story.append(Paragraph("Developer Meta-Prompts: Digital Twin &amp; Engine", title_style))
    story.append(Paragraph("Architectural synthesis prompts used to construct the digital twin and detection pipeline", subtitle_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("PROMPT 1: Digital Twin Hydraulic Simulator Synthesis", h2_style))
    story.append(Spacer(1, 4))
    sim_meta = """Design and implement an in-memory, zero-dependency Python Digital Twin simulator
modeling commercial airport restroom plumbing infrastructure for Pune International Airport (PNQ).
Requirements:
1. Model 97 instrumented fixtures: 48 flush valves (K-10673), 32 urinals, 17 auto faucets.
2. Distribute across 12 restrooms in 4 terminals: Terminal 1, Terminal 2, Terminal 3, Arrivals.
3. Simulate realistic airport passenger traffic curves with morning, afternoon, and evening flight banks.
4. For each fixture, maintain stateful parameters: flow_lpm, static/dynamic pressure_bar (nominal 3.0),
   optical IR distance occupancy, cumulative flush count, battery voltage, and health score (0-100).
5. Support scenario injection methods: continuous leak (diaphragm tear), phantom flush (solenoid drift),
   sensor failure (flatline), device degradation (cycle fatigue), and passenger occupancy spikes.
6. Execute deterministically every 2 seconds (1 tick = 1 sim minute) without blocking asyncio loops."""
    story.append(make_code_table(sim_meta, font_size=7.2, lead=9.2))
    story.append(Spacer(1, 10))

    story.append(Paragraph("PROMPT 2: Dual-Layer Detection &amp; Multimodal Sensor Fusion", h2_style))
    story.append(Spacer(1, 4))
    engine_meta = """Build a high-precision, low-latency dual-layer anomaly detection and sensor fusion engine.
Layer 1 (Deterministic Rules):
- Continuous Leak: Trigger if flow > 0.5 L/min AND occupancy == 0 AND flushes == 0 for >= 3 minutes.
- Phantom Flush: Trigger if flow pulses > 5.0 L/min for 3-5 seconds without traveler occupancy.
- Sensor Freeze: Trigger if optical occupancy == 1 for > 30 minutes with zero flush actuation.
Layer 2 (Multimodal Fusion Model):
- Compute 0-100 Anomaly Score via multi-factor weighting: Flow Deviation vs Diurnal Baseline (30%),
  Occupancy Mismatch (20%), Acoustic Hydrophone Flutter (15%), Pressure Drop (15%), Traveler QR (20%).
- Calculate Bayesian Leak Confidence (0.0 to 1.0).
- Quantify water loss: Daily Liters = flow_lpm * 1440; Monthly Liters = Daily * 30.
- Calculate cost impact using commercial municipal tariff rate (₹48.50 per 1,000 Liters)."""
    story.append(make_code_table(engine_meta, font_size=7.2, lead=9.2))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 12: Developer Meta-Prompts — Hydrophone & Vector CAD Schematics
    # =========================================================================
    story.append(Paragraph("Developer Meta-Prompts: Hydrophone &amp; CAD Schematics", title_style))
    story.append(Paragraph("Physics-based acoustic synthesis and architectural CAD vector visualization prompts", subtitle_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("PROMPT 3: Acoustic Hydrophone Cavitation Audio &amp; Oscilloscope", h2_style))
    story.append(Spacer(1, 4))
    audio_meta = """Implement an industrial acoustic hydrophone telemetry synthesizer and real-time visualizer:
1. Backend Profile Generator:
   - For nominal fixtures: 420 Hz fundamental sine wave, 2.1% THD (Laminar Full Flush).
   - For diaphragm tear leaks: 2,420 Hz turbulent screech, 14.5 Hz flutter, 38.4% THD (Cavitation).
   - For solenoid phantom cycling: 120 Hz electrical latch hum, square wave harmonics.
   - For quiescent baseline: 0 Hz electronic sensor thermal noise floor.
2. Frontend Web Audio API & Canvas Oscilloscope:
   - Create browser AudioContext with OscillatorNode, GainNode, and LFO flutter modulation.
   - Render a real-time oscilloscope canvas (480x90) with subtle reticle grid and center baseline.
   - Dynamically transition wave color from cyan (#00A3E0) to warning red (#FF4D5A) upon cavitation."""
    story.append(make_code_table(audio_meta, font_size=7.2, lead=9.2))
    story.append(Spacer(1, 10))

    story.append(Paragraph("PROMPT 4: Interactive Kohler K-10673 CAD Exploded Schematics", h2_style))
    story.append(Spacer(1, 4))
    cad_meta = """Create an architectural vector SVG exploded diagram modeling the Kohler K-10673 Tripoint Flushometer:
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
- Clicking any part opens an engineering spec callout displaying part number, price, and depot shelf location."""
    story.append(make_code_table(cad_meta, font_size=7.2, lead=9.2))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 13: Developer Meta-Prompts — Portfolio & Scope 2/3 Carbon Nexus
    # =========================================================================
    story.append(Paragraph("Developer Meta-Prompts: Fleet Portfolio &amp; Carbon Nexus", title_style))
    story.append(Paragraph("Multi-facility aggregation and institutional greenhouse gas accounting prompts", subtitle_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("PROMPT 5: Multi-Airport Fleet Portfolio &amp; National Benchmarking", h2_style))
    story.append(Spacer(1, 4))
    port_meta = """Create a multi-airport fleet aggregation engine for aviation facility directors:
Airports to model:
1. Pune International Airport (PNQ): Live Digital Twin, 97 fixtures, 28,400 daily pax, ₹443k/mo saved.
2. Mumbai Chhatrapati Shivaji T2 (BOM): Synthetic Fleet Twin, 184 fixtures, 74,000 daily pax, ₹1.25M/mo saved.
3. Delhi Indira Gandhi T3 (DEL): Synthetic Fleet Twin, 312 fixtures, 142,000 daily pax, ₹1.83M/mo saved.
Outputs:
- Consolidated national metrics: 593 fixtures, 260,900 L/day conserved, ₹3.52M/month in tariff avoidance.
- Header dropdown switcher enabling instant context switching between airports.
- Benchmark dialog displaying national sustainability ranking table and composite facility health comparison."""
    story.append(make_code_table(port_meta, font_size=7.2, lead=9.2))
    story.append(Spacer(1, 10))

    story.append(Paragraph("PROMPT 6: Scope 2/3 GHG Carbon Nexus &amp; LEED Scorecard", h2_style))
    story.append(Spacer(1, 4))
    esg_meta = """Implement an institutional ESG water-energy nexus and green building rating engine:
Constants (Central Electricity Authority CEA India Database):
- Municipal water pumping energy intensity: 1.82 kWh per 1,000 Liters (kL).
- CEA Grid emission factor: 0.82 kg CO2e per kWh -> 1.4924 kg CO2e per kL avoided.
- Tree absorption: 21.8 kg CO2 per tree-year; Tanker truck capacity: 12,000 Liters.
LEED v4.1 Operations & Maintenance Scorecard:
- WE Prerequisite 1: Indoor Water Use Reduction (20% Baseline) -> Compliant (>45% achieved).
- WE Credit 1: Indoor Water Efficiency -> 5/6 Points.
- WE Credit 2: Water Sub-metering & AI Monitoring -> 2/2 Points.
- EA Credit 1: Pumping Energy Reduction -> 4/5 Points.
- Output: Composite Score 92/100 (LEED Platinum Ready).
- Generate verifiable digital certificate with cryptographic SHA-256 validation seal."""
    story.append(make_code_table(esg_meta, font_size=7.2, lead=9.2))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 14: Developer Meta-Prompts — CMMS Work Order & Weibull Lifecycle
    # =========================================================================
    story.append(Paragraph("Developer Meta-Prompts: CMMS &amp; Weibull Lifecycle", title_style))
    story.append(Paragraph("Maximo work order formatting and mathematical mechanical fatigue modeling prompts", subtitle_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("PROMPT 7: IBM Maximo &amp; SAP PM CMMS Work Order Generator", h2_style))
    story.append(Spacer(1, 4))
    cmms_meta = """Build an industrial Computerized Maintenance Management System (CMMS) work order generator
compatible with IBM Maximo Asset Management (v7.6.1) and SAP Plant Maintenance (PM).
Fields:
- Work Order Number: WO-2026-XXXXX
- Asset Tag: KOHLER-{device_id}; Functional Location: PNQ-T2-R14-STALL-03
- Failure Code: CONTINUOUS_LEAK; Safety Mandate: Level 2 Domestic Water System Lockout/Tagout (LOTO)
- Required Spare: Kohler OEM part number, price, and reserved storage location
- Job Plan: 8 numbered sequential steps (isolate stopcock, remove flange, replace diaphragm, torque 18 Nm, verify flow)
- Aviation barcode scan code & technician digital signature block
- 1-click printable job card modal."""
    story.append(make_code_table(cmms_meta, font_size=7.2, lead=9.2))
    story.append(Spacer(1, 10))

    story.append(Paragraph("PROMPT 8: Weibull Asset Lifecycle Hazard Rate Modeler", h2_style))
    story.append(Spacer(1, 4))
    weibull_meta = """Formulate an asset lifecycle degradation and predictive maintenance model for solenoid flushometers:
1. Cycle Wear Metric: Completed actuations vs 500,000 rated cycle lifetime.
2. Weibull Hazard Rate Formulation:
   - Shape parameter beta = 2.8 (mechanical wear-out regime), scale parameter eta = 500,000 cycles.
   - Cumulative failure risk: R(t) = 1 - exp(-((cycles + delta_7d) / eta)^beta).
3. Vibration Chatter Index (0 to 100): Quantify armature micro-bounce and water hammer transient spikes.
4. Output: Fleet degradation overview ranking top-5 at-risk assets with recommended preventive intervention."""
    story.append(make_code_table(weibull_meta, font_size=7.2, lead=9.2))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 15: Developer Meta-Prompts — Passenger QR Fusion & Ops Center UI
    # =========================================================================
    story.append(Paragraph("Developer Meta-Prompts: Traveler QR &amp; UI Design", title_style))
    story.append(Paragraph("Multimodal traveler crowd-sensing fusion and high-contrast control room design prompts", subtitle_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("PROMPT 9: Multimodal Passenger QR Feedback Ingestion &amp; Fusion", h2_style))
    story.append(Spacer(1, 4))
    qr_meta = """Design a traveler mobile feedback ingestion engine that boosts physical sensor confidence:
1. API Endpoint: POST /api/feedback accepting restroom_id, issue_category, stall_number, and optional comment.
2. Multimodal Matching Logic:
   - Match reported restroom and stall to active device in digital twin.
   - If device has an open anomaly alert, apply a +15% Bayesian fusion boost to leak confidence (capped at 0.99).
   - If priority was P2, escalate to P1 due to traveler visibility and public brand impact.
3. Return confirmation payload showing elevated confidence and matched device ID."""
    story.append(make_code_table(qr_meta, font_size=7.2, lead=9.2))
    story.append(Spacer(1, 10))

    story.append(Paragraph("PROMPT 10: Industrial High-Contrast Dark-Theme Ops Center UI", h2_style))
    story.append(Spacer(1, 4))
    ui_meta = """Redesign the AquaGuard frontend into a research-grade commercial facility command center.
Visual Language:
- Palette: Dark control-room theme (Background #080B10, Panels #10151C, Borders #202833).
- Primary Text: #F4F7FA; Muted Text: #8B96A5; Kohler Accent: #00A3E0.
- State Colors: Normal #35D07F, Warning #F5B942, Critical #FF4D5A.
- Layout: Spatial Facility Twin Map, Terminal Status Cards, 24-Hour Diurnal Timeline Canvas,
  Dedicated Incident Workspace with OEM spare cards, CAD schematics, and closed-loop verification stepper.
- Responsive, zero npm build step, pure ES6 HTML/CSS/JS served directly via FastAPI."""
    story.append(make_code_table(ui_meta, font_size=7.2, lead=9.2))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 16: Custom Specialized AI Prompts for Facility Operations
    # =========================================================================
    story.append(Paragraph("Custom Operational Prompts for Facility Teams", title_style))
    story.append(Paragraph("Specialized operational prompt templates designed for facility directors and plumbing leads", subtitle_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("CUSTOM PROMPT 1: Automated Shift-Handoff Intelligence Briefing", h2_style))
    story.append(Spacer(1, 4))
    custom1 = """[CONTEXT: Facility Health Hierarchy, Open Incidents, Resolved Ledger, Spares Depletion]
You are AquaGuard AI. Compose an executive Shift-Handoff Briefing for the incoming Terminal Facilities Lead:
1. Executive Summary: 1-sentence composite health rating and open P1/P2 count.
2. Active Critical Incidents: Device ID, location, root cause, assigned technician, and SLA minutes remaining.
3. Closed-Loop Achievements: Water volume banked to ledger during the outgoing shift and commercial savings.
4. OEM Spares Advisory: Depot parts with inventory <= 3 units requiring procurement requisition.
5. High-Risk Assets: Top 2 fixtures exhibiting > 70% Weibull 7-day failure probability.
Tone: Crisp, military-grade operational brevity. Use markdown bullet points with bold metrics."""
    story.append(make_code_table(custom1, font_size=7.2, lead=9.2))
    story.append(Spacer(1, 10))

    story.append(Paragraph("CUSTOM PROMPT 2: Contractor SLA Breach Enforcement &amp; Escalation", h2_style))
    story.append(Spacer(1, 4))
    custom2 = """[CONTEXT: Incident ID, Device ID, Zone, Assigned Technician, Current SLA Remaining Seconds]
The SLA countdown for incident {{incident_id}} on fixture {{device_id}} has reached {{sla_seconds}} seconds.
Generate an automated emergency CAD dispatch escalation payload:
1. Broadcast high-priority SMS/WhatsApp alert to Plumbing Supervisor:
   "URGENT: P1 SLA Breach Imminent on {{device_id}} ({{zone}}). Unmitigated loss: {{flow_lpm}} L/min.
   Technician {{tech_name}} has not verified arrival. Backup specialist required immediately."
2. Log breach warning to official compliance audit log with ISO timestamp.
3. Surface priority dispatch banner in AI Command Center dashboard."""
    story.append(make_code_table(custom2, font_size=7.2, lead=9.2))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {PDF_PATH} ({os.path.getsize(PDF_PATH)} bytes)")


if __name__ == "__main__":
    generate_pdf()

