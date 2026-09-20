"""Generator for presentation/KOHLER_AquaGuard_AI.pdf.

Generates a publication-grade, 4-slide executive presentation deck
formatted in widescreen landscape (11 x 8.5 inch) for Track 2 submission.
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.pdfgen import canvas

PDF_PATH = os.path.join("presentation", "KOHLER_AquaGuard_AI.pdf")

# Palette
DARK_BG = colors.HexColor("#080B10")
PANEL_BG = colors.HexColor("#10151C")
BORDER_COLOR = colors.HexColor("#202833")
PRIMARY_TEXT = colors.HexColor("#F4F7FA")
MUTED_TEXT = colors.HexColor("#8B96A5")
KOHLER_CYAN = colors.HexColor("#00A3E0")
ALERT_RED = colors.HexColor("#FF4D5A")
SUCCESS_GREEN = colors.HexColor("#35D07F")
WARN_AMBER = colors.HexColor("#F5B942")
GOLD_ACCENT = colors.HexColor("#C09A53")
CARD_BG = colors.HexColor("#141A22")
CODE_BG = colors.HexColor("#0C1017")


class PresentationCanvas(canvas.Canvas):
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
            self.draw_slide_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_slide_decorations(self, total_pages):
        self.saveState()
        # Full background
        self.setFillColor(DARK_BG)
        self.rect(0, 0, 11 * inch, 8.5 * inch, fill=1, stroke=0)

        # Header rule
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(1)
        self.line(0.5 * inch, 8.0 * inch, 10.5 * inch, 8.0 * inch)

        # Header text
        self.setFont("Helvetica-Bold", 9)
        self.setFillColor(KOHLER_CYAN)
        self.drawString(0.5 * inch, 8.12 * inch, "KOHLER AQUAGUARD AI")
        self.setFont("Helvetica", 9)
        self.setFillColor(MUTED_TEXT)
        self.drawString(2.3 * inch, 8.12 * inch, "·  Track 2 Smart Facility & Sustainability Manager  ·  Executive Pitch Deck")

        # Footer rule
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(1)
        self.line(0.5 * inch, 0.55 * inch, 10.5 * inch, 0.55 * inch)

        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED_TEXT)
        self.drawString(0.5 * inch, 0.38 * inch, "KOHLER-MITWPU INNOVATION HACKATHON  ·  TRACK 2 FINAL DELIVERABLE  ·  PUNE AIRPORT DEPLOYMENT")

        slide_str = f"Slide {self._pageNumber} of {total_pages}"
        self.drawRightString(10.5 * inch, 0.38 * inch, slide_str)
        self.restoreState()


def generate_deck():
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=landscape(letter),
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )

    styles = getSampleStyleSheet()
    slide_title = ParagraphStyle('STitle', fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=PRIMARY_TEXT)
    slide_sub = ParagraphStyle('SSub', fontName='Helvetica', fontSize=11, leading=15, textColor=MUTED_TEXT)
    h2_style = ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=KOHLER_CYAN)
    card_h = ParagraphStyle('CardH', fontName='Helvetica-Bold', fontSize=10.5, leading=14, textColor=PRIMARY_TEXT)
    body_style = ParagraphStyle('Body', fontName='Helvetica', fontSize=8.5, leading=12, textColor=PRIMARY_TEXT)
    muted_body = ParagraphStyle('MutedBody', fontName='Helvetica', fontSize=8, leading=11, textColor=MUTED_TEXT)
    big_stat = ParagraphStyle('BigStat', fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=KOHLER_CYAN)

    story = []

    # =========================================================================
    # SLIDE 1: Problem + Solution
    # =========================================================================
    story.append(Paragraph("KOHLER AquaGuard AI", slide_title))
    story.append(Paragraph("Smart Facility &amp; Sustainability Manager  ·  Commercial Airport Operations", slide_sub))
    story.append(Spacer(1, 14))

    # Two column: Problem vs Solution
    prob_content = [
        Paragraph("<font color='#FF4D5A'><b>THE COMMERCIAL FACILITY CHALLENGE</b></font>", card_h),
        Spacer(1, 6),
        Paragraph("• <b>Unnoticed Water Wastage:</b> A single leaking flush valve loses 2.7 L/min (3,888 L/day = 116,640 L/month = ₹5,657/month).", body_style),
        Spacer(1, 4),
        Paragraph("• <b>Blind Maintenance:</b> High-traffic airport restrooms rely on periodic visual patrols, catching leaks hours or days after occurrence.", body_style),
        Spacer(1, 4),
        Paragraph("• <b>Phantom Flushes &amp; Wear:</b> Unsynchronized solenoids and pressure surges cause ghost flushes and premature component fatigue.", body_style),
        Spacer(1, 4),
        Paragraph("• <b>Manual Hygiene Monitoring:</b> Scheduled cleaning ignores volatile flight arrival surges, leading to service complaints and passenger hygiene breaches.", body_style),
    ]

    sol_content = [
        Paragraph("<font color='#35D07F'><b>THE AQUAGUARD AI AUTONOMOUS SOLUTION</b></font>", card_h),
        Spacer(1, 6),
        Paragraph("• <b>Sub-Second Detection:</b> Continuous flow and phantom flush rules detect anomalies within 3 seconds of onset.", body_style),
        Spacer(1, 4),
        Paragraph("• <b>Physics-Based Sensor Fusion:</b> Correlates flow, IR occupancy, acoustic cavitation (2,420 Hz), and traveler QR feedback.", body_style),
        Spacer(1, 4),
        Paragraph("• <b>Automated Computer-Aided Dispatch:</b> Automatically cuts work orders, reserves Kohler OEM spares, and enforces 15-min SLAs.", body_style),
        Spacer(1, 4),
        Paragraph("• <b>Closed-Loop Verification:</b> Live telemetry mathematically verifies flow reduction to 0.00 L/min before banking accredited savings.", body_style),
    ]

    comp_table = Table([[prob_content, sol_content]], colWidths=[4.9 * inch, 4.9 * inch])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#1A0F12")),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor("#0F1A14")),
        ('BOX', (0, 0), (0, 0), 1, ALERT_RED),
        ('BOX', (1, 0), (1, 0), 1, SUCCESS_GREEN),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 14))

    # Pipeline Ribbon
    ribbon_p = Paragraph(
        "<font color='#00A3E0'><b>CORE TRANSFORMATION:</b></font>  "
        "IoT Telemetry  &rarr;  AI Anomaly Intelligence  &rarr;  Water Waste Detection  &rarr;  "
        "Predictive Maintenance  &rarr;  Automated Dispatch  &rarr;  Verified Conservation Ledger",
        ParagraphStyle('Ribbon', fontName='Helvetica-Bold', fontSize=9, leading=13, textColor=PRIMARY_TEXT, alignment=1))
    
    tagline_p = Paragraph(
        "<i>\"From reactive manual maintenance to autonomous, research-grade facility intelligence.\"</i>",
        ParagraphStyle('Tag', fontName='Helvetica-Bold', fontSize=10, leading=14, textColor=GOLD_ACCENT, alignment=1))

    bottom_box = Table([[ribbon_p], [tagline_p]], colWidths=[9.9 * inch])
    bottom_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PANEL_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(bottom_box)

    story.append(PageBreak())

    # =========================================================================
    # SLIDE 2: Architecture
    # =========================================================================
    story.append(Paragraph("End-to-End System Architecture", slide_title))
    story.append(Paragraph("Modular, decoupled industrial intelligence stack for commercial aviation infrastructure", slide_sub))
    story.append(Spacer(1, 10))

    # Architecture Pipeline Grid (4 columns)
    stage1 = [
        Paragraph("<font color='#00A3E0'><b>1. INGESTION &amp; TWIN</b></font>", card_h),
        Spacer(1, 4),
        Paragraph("• 97 Smart Fixtures (Tripoint)", body_style),
        Paragraph("• 12 Restrooms · 4 Terminals", body_style),
        Paragraph("• Flow (L/min) · Pressure (bar)", body_style),
        Paragraph("• Optical IR Occupancy", body_style),
        Paragraph("• Hydrophone Cavitation (Hz)", body_style),
        Paragraph("• MQTT / Telemetry API Gateway", body_style),
    ]

    stage2 = [
        Paragraph("<font color='#F5B942'><b>2. DETECTION &amp; ML</b></font>", card_h),
        Spacer(1, 4),
        Paragraph("• Diurnal Baseline Subtraction", body_style),
        Paragraph("• Deterministic Continuous Flow", body_style),
        Paragraph("• Solenoid Phantom Cycle Rules", body_style),
        Paragraph("• Multimodal Sensor Fusion", body_style),
        Paragraph("• Bayesian Leak Confidence", body_style),
        Paragraph("• Weibull Degradation Hazard", body_style),
    ]

    stage3 = [
        Paragraph("<font color='#FF4D5A'><b>3. INCIDENT INTEL</b></font>", card_h),
        Spacer(1, 4),
        Paragraph("• Canonical Incident Schema", body_style),
        Paragraph("• P1/P2/P3 SLA Dynamic Timer", body_style),
        Paragraph("• Kohler OEM Spare Matching", body_style),
        Paragraph("• Depot Shelf Inventory Sync", body_style),
        Paragraph("• CAD Technician Dispatch", body_style),
        Paragraph("• Maximo / SAP PM Work Orders", body_style),
    ]

    stage4 = [
        Paragraph("<font color='#35D07F'><b>4. VERIFY &amp; LEDGER</b></font>", card_h),
        Spacer(1, 4),
        Paragraph("• Real-Time Flow Decay Probe", body_style),
        Paragraph("• Zero-Leak Baseline Audit", body_style),
        Paragraph("• Fixture Health Restoration", body_style),
        Paragraph("• Scope 2/3 GHG Carbon Nexus", body_style),
        Paragraph("• LEED v4.1 Platinum Scorecard", body_style),
        Paragraph("• SHA-256 Digital Certificate", body_style),
    ]

    pipe_table = Table([[stage1, stage2, stage3, stage4]], colWidths=[2.45 * inch, 2.45 * inch, 2.45 * inch, 2.45 * inch])
    pipe_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PANEL_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(pipe_table)
    story.append(Spacer(1, 10))

    # Bottom bar: AI Command Center (ReAct) Integration
    ai_box = [
        Paragraph("<font color='#00A3E0'><b>GROUNDED AI COMMAND CENTER (REACT REASONING LAYER)</b></font>", card_h),
        Paragraph(
            "Natural Language Operations Engine operating via strict function-calling whitelist: "
            "<code>get_water_waste_heatmap()</code>, <code>get_facility_health_hierarchy()</code>, "
            "<code>get_device_detail()</code>, <code>simulate_inaction()</code>. "
            "<b>Zero Generative Hallucination:</b> All metrics, tariffs (₹48.50/kL), and volumes are computed by deterministic engines before being explained.",
            body_style
        )
    ]
    ai_table = Table([[ai_box]], colWidths=[9.9 * inch])
    ai_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CARD_BG),
        ('BOX', (0, 0), (-1, -1), 1, KOHLER_CYAN),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(ai_table)

    story.append(PageBreak())

    # =========================================================================
    # SLIDE 3: Live Demo & Innovation Pack
    # =========================================================================
    story.append(Paragraph("Live Demonstration &amp; Technical Innovations", slide_title))
    story.append(Paragraph("Autonomous closed-loop incident lifecycle verified on Pune Airport Terminal 2", slide_sub))
    story.append(Spacer(1, 10))

    # 4 Demo Step Cards
    d1 = [
        Paragraph("<font color='#00A3E0'><b>STEP 1: INJECT LEAK</b></font>", card_h),
        Spacer(1, 4),
        Paragraph("• Simulate continuous leak on <code>FV-182</code> (Restroom 14, Stall 03).", body_style),
        Paragraph("• Flow jumps to <b>2.70 L/min</b>.", body_style),
        Paragraph("• Zero traveler occupancy.", body_style),
        Paragraph("• Line pressure steady at 3.0 bar.", body_style),
    ]

    d2 = [
        Paragraph("<font color='#FF4D5A'><b>STEP 2: DETECTION &amp; CAD</b></font>", card_h),
        Spacer(1, 4),
        Paragraph("• Anomaly score spikes to <b>94/100</b>.", body_style),
        Paragraph("• Acoustic hydrophone detects <b>2,420 Hz screech</b> (14.5 Hz flutter).", body_style),
        Paragraph("• <b>CAD Schematics:</b> EPDM Diaphragm pulses red in exploded CAD view.", body_style),
        Paragraph("• Loss flagged: <b>116,640 L/month</b>.", body_style),
    ]

    d3 = [
        Paragraph("<font color='#F5B942'><b>STEP 3: 1-CLICK DISPATCH</b></font>", card_h),
        Spacer(1, 4),
        Paragraph("• Priority <b>P1 Critical Alert</b>.", body_style),
        Paragraph("• 15-minute SLA timer countdown.", body_style),
        Paragraph("• OEM Spare Requisitioned: <b>KOHLER-GP1138930</b> (T2 Rack B-04).", body_style),
        Paragraph("• CMMS Work Order <b>WO-2026-00182</b> generated with LOTO safety protocol.", body_style),
    ]

    d4 = [
        Paragraph("<font color='#35D07F'><b>STEP 4: VERIFY &amp; BANK</b></font>", card_h),
        Spacer(1, 4),
        Paragraph("• Technician replaces diaphragm.", body_style),
        Paragraph("• Verification probe confirms flow drops back to <b>0.00 L/min</b>.", body_style),
        Paragraph("• Fixture health restored: <b>98/100</b>.", body_style),
        Paragraph("• <b>116,640 Liters saved</b> banked to official sustainability ledger.", body_style),
    ]

    demo_table = Table([[d1, d2, d3, d4]], colWidths=[2.45 * inch, 2.45 * inch, 2.45 * inch, 2.45 * inch])
    demo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PANEL_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(demo_table)
    story.append(Spacer(1, 10))

    # Triple Innovation Highlights
    inno1 = [
        Paragraph("<font color='#00A3E0'><b>Acoustic Cavitation Hydrophone</b></font>", card_h),
        Paragraph("Web Audio API physical frequency synthesis (420 Hz laminar, 2,420 Hz cavitation tear, 120 Hz solenoid hum) with real-time canvas oscilloscope.", muted_body)
    ]
    inno2 = [
        Paragraph("<font color='#00A3E0'><b>Exploded CAD Schematics</b></font>", card_h),
        Paragraph("Interactive vector architectural diagram of Kohler K-10673 flushometer with dynamic drop-shadow fault highlighting and OEM parts registry.", muted_body)
    ]
    inno3 = [
        Paragraph("<font color='#00A3E0'><b>National Portfolio Fleet</b></font>", card_h),
        Paragraph("Multi-airport portfolio switcher across Pune PNQ (Live), Mumbai BOM T2, and Delhi DEL T3 aggregating 593 fixtures and 260.9k L/day.", muted_body)
    ]

    inno_table = Table([[inno1, inno2, inno3]], colWidths=[3.25 * inch, 3.25 * inch, 3.25 * inch])
    inno_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CARD_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(inno_table)

    story.append(PageBreak())

    # =========================================================================
    # SLIDE 4: Operational & Sustainability Impact
    # =========================================================================
    story.append(Paragraph("Measurable Enterprise Impact &amp; Value", slide_title))
    story.append(Paragraph("Quantified operational, environmental, and financial returns for commercial facility managers", slide_sub))
    story.append(Spacer(1, 10))

    # 4 Quadrants
    q1 = [
        Paragraph("<font color='#00A3E0'><b>WATER STEWARDSHIP</b></font>", card_h),
        Spacer(1, 4),
        Paragraph("• <b>116,640 L/month</b> conserved per resolved critical leak.", body_style),
        Paragraph("• <b>260,900 L/day</b> saved across 3 monitored airports.", body_style),
        Paragraph("• <b>₹3,522,150/month</b> in commercial utility tariff costs avoided (@ ₹48.50/kL).", body_style),
        Paragraph("• <b>11.9 commercial water tankers</b> eliminated per single incident.", body_style),
    ]

    q2 = [
        Paragraph("<font color='#35D07F'><b>OPERATIONAL EXCELLENCE</b></font>", card_h),
        Spacer(1, 4),
        Paragraph("• <b>Automated P1 Dispatch:</b> Technician dispatched within 3 seconds of leak confirmation.", body_style),
        Paragraph("• <b>15-Minute SLA Guarantee:</b> Real-time countdown prevents regulatory breach.", body_style),
        Paragraph("• <b>Zero Manual Logging:</b> Automated IBM Maximo / SAP PM work order generation.", body_style),
        Paragraph("• <b>100% Closed-Loop Verification:</b> Eliminates false maintenance sign-offs.", body_style),
    ]

    q3 = [
        Paragraph("<font color='#F5B942'><b>PREDICTIVE ASSET HEALTH</b></font>", card_h),
        Spacer(1, 4),
        Paragraph("• <b>Weibull Hazard Modeling:</b> Flags failure risk before physical rupture occurs.", body_style),
        Paragraph("• <b>Vibration Chatter Index:</b> Solves water hammer and premature coil burnout.", body_style),
        Paragraph("• <b>Zero Flight Bank Downtime:</b> Proactive spares staging in T2 Depot Shelf B-04.", body_style),
        Paragraph("• <b>Hardware Payback:</b> Sensor retrofit amortized in 4.8 months.", body_style),
    ]

    q4 = [
        Paragraph("<font color='#C09A53'><b>ESG &amp; GREEN BUILDING</b></font>", card_h),
        Spacer(1, 4),
        Paragraph("• <b>Scope 2/3 GHG Avoidance:</b> 212.7 kg CO₂e offset monthly (1.82 kWh/kL CEA nexus).", body_style),
        Paragraph("• <b>LEED v4.1 Platinum Tier:</b> 92/100 points achieved on water efficiency credits.", body_style),
        Paragraph("• <b>Cryptographic Assurance:</b> Tamper-proof SHA-256 digital certificate seals.", body_style),
        Paragraph("• <b>Adaptive Hygiene Threshold:</b> Automatic janitorial dispatch on flight deplaning.", body_style),
    ]

    quad_table = Table([[q1, q2], [q3, q4]], colWidths=[4.9 * inch, 4.9 * inch], rowHeights=[1.7 * inch, 1.7 * inch])
    quad_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PANEL_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(quad_table)
    story.append(Spacer(1, 8))

    # Final Banner Mantra
    mantra = Paragraph(
        "<b>DETECT  &nbsp;&middot;&nbsp;  DIAGNOSE  &nbsp;&middot;&nbsp;  PRIORITIZE  &nbsp;&middot;&nbsp;  DISPATCH  &nbsp;&middot;&nbsp;  CONSERVE</b>",
        ParagraphStyle('Mantra', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=PRIMARY_TEXT, alignment=1))
    mantra_box = Table([[mantra]], colWidths=[9.9 * inch])
    mantra_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#0284C7")),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(mantra_box)

    doc.build(story, canvasmaker=PresentationCanvas)
    print(f"Successfully generated {PDF_PATH} ({os.path.getsize(PDF_PATH)} bytes)")


if __name__ == "__main__":
    generate_deck()
