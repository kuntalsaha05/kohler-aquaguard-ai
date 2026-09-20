"""KOHLER AquaGuard AI — Field Technician Dispatch Webhook & Notification Engine.

Broadcasts multi-channel technician dispatch alerts (Simulated WhatsApp Enterprise,
SMS, and Airport Facilities CAD) with exact fixture location, root cause,
and genuine Kohler OEM part pickup locations.
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

TECHNICIAN_ROSTER = {
    "Priya Sharma": {"phone": "+91 98201 44512", "role": "Senior Plumbing Specialist", "zone": "Terminal 2 & Terminal 3"},
    "Arjun Patel": {"phone": "+91 98201 88321", "role": "Facilities Field Technician", "zone": "Terminal 1 & Arrivals"},
    "Ramesh K": {"phone": "+91 98201 77199", "role": "Master Mechanical Specialist", "zone": "Fleet Risers & Pressure"},
}

DISPATCH_LOG: List[Dict[str, Any]] = []


class DispatchNotificationRequest(BaseModel):
    incident_id: str
    device_id: str
    zone: str
    priority: str = "P1"
    root_cause: str = "Flush Valve Diaphragm Tear"
    oem_part: str = "KOHLER-GP1138930"
    stock_location: str = "T2 Depot Rack B-04"
    technician: str = "Priya Sharma"
    sla_minutes: int = 15


def send_dispatch_notification(req: DispatchNotificationRequest) -> Dict[str, Any]:
    """Generates a field dispatch alert and records the simulated WhatsApp/SMS transmission."""
    tech_info = TECHNICIAN_ROSTER.get(req.technician, TECHNICIAN_ROSTER["Priya Sharma"])
    dispatch_id = f"DSP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
    ts = datetime.now(timezone.utc).isoformat()

    msg_text = (
        f"🚨 *KOHLER AQUAGUARD {req.priority} DISPATCH*\\n"
        f"• *Fixture:* {req.device_id} ({req.zone})\\n"
        f"• *Root Cause:* {req.root_cause}\\n"
        f"• *OEM Part:* {req.oem_part} (Pick up at {req.stock_location})\\n"
        f"• *SLA Target:* {req.sla_minutes} min response window.\\n"
        f"Open Mobile Console: http://127.0.0.1:8000/ui/mobile.html"
    )

    record = {
        "dispatch_id": dispatch_id,
        "channel": "WHATSAPP_ENTERPRISE_CAD",
        "technician": req.technician,
        "phone": tech_info["phone"],
        "incident_id": req.incident_id,
        "device_id": req.device_id,
        "zone": req.zone,
        "priority": req.priority,
        "root_cause": req.root_cause,
        "oem_part": req.oem_part,
        "stock_location": req.stock_location,
        "sla_minutes": req.sla_minutes,
        "message_body": msg_text,
        "transmission_status": "DELIVERED",
        "sent_at": ts,
    }

    DISPATCH_LOG.append(record)
    return record


def get_dispatch_log(limit: int = 25) -> List[Dict[str, Any]]:
    """Returns recent dispatch transmissions."""
    return list(reversed(DISPATCH_LOG[-limit:]))
