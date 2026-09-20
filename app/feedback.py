"""KOHLER AquaGuard AI — Passenger QR Code Feedback & Multimodal Fusion.

Ingests traveler QR code feedback from airport restroom door scans,
cross-correlates passenger reports with IoT physical flow telemetry,
and dynamically boosts incident detection confidence and SLA priority.
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class PassengerFeedback(BaseModel):
    restroom_id: str
    issue_category: str  # "running_toilet", "water_leak", "low_pressure", "unclean", "sensor_dead"
    rating: int = 1  # 1 to 5 stars
    stall_number: Optional[str] = "Stall 2"
    device_id: Optional[str] = None
    comment: Optional[str] = "Toilet water is constantly running into the bowl"
    passenger_flight: Optional[str] = "AI-852"


FEEDBACK_LOG: List[Dict[str, Any]] = []


def ingest_passenger_feedback(fb: PassengerFeedback, store) -> Dict[str, Any]:
    """Ingests passenger feedback, matches against active alerts/devices, and fuses telemetry."""
    feedback_id = f"FB-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
    ts = datetime.now(timezone.utc).isoformat()

    feedback_entry = {
        "feedback_id": feedback_id,
        "restroom_id": fb.restroom_id,
        "issue_category": fb.issue_category,
        "rating": fb.rating,
        "stall_number": fb.stall_number,
        "device_id": fb.device_id,
        "comment": fb.comment,
        "passenger_flight": fb.passenger_flight,
        "timestamp": ts,
        "correlated_incident_id": None,
        "fusion_boost_applied": False,
    }

    # Search for matching active alert/incident in this restroom
    matching_alert = None
    for alert in store.alerts:
        if alert.status == "OPEN":
            # Match by device ID or zone/restroom
            if fb.device_id and alert.device_id == fb.device_id:
                matching_alert = alert
                break
            elif alert.zone == fb.restroom_id or fb.restroom_id in alert.zone:
                matching_alert = alert
                break

    # If no active alert, check devices in this zone with non-zero flow
    if not matching_alert:
        for dev in store.devices.values():
            if dev.zone == fb.restroom_id and dev.flow_lpm > 0.5:
                # Find or wait for alert
                for a in store.alerts:
                    if a.device_id == dev.device_id and a.status == "OPEN":
                        matching_alert = a
                        break

    if matching_alert:
        # Boost confidence & escalate
        old_conf = getattr(matching_alert, "leak_confidence", 0.85)
        new_conf = min(0.99, round(old_conf + 0.12, 2))
        matching_alert.leak_confidence = new_conf

        # Escalate priority to P1 if running toilet / leak
        if fb.issue_category in ("running_toilet", "water_leak"):
            matching_alert.priority = "P1"
            matching_alert.sla_minutes = 15
            matching_alert.sla_remaining_seconds = min(getattr(matching_alert, "sla_remaining_seconds", 900), 900)

        # Update canonical incident object
        matched_alert_id = getattr(matching_alert, "alert_id", getattr(matching_alert, "id", "ALT-001"))
        inc_id = None
        for inc in store.incidents:
            if (getattr(inc, "alert_id", "") == matched_alert_id or
                getattr(inc, "incident_id", "") == f"INC-{matched_alert_id}" or
                getattr(inc, "device_id", "") == matching_alert.device_id):
                inc.leak_confidence = new_conf
                inc.priority = matching_alert.priority
                inc.timeline.append({
                    "timestamp": ts,
                    "event": "PASSENGER_CROWD_CORRELATION",
                    "detail": f"Traveler QR scan report ({fb.issue_category}): \"{fb.comment}\". Fusion confidence elevated to {new_conf:.0%}.",
                })
                inc_id = inc.incident_id
                break

        feedback_entry["correlated_incident_id"] = inc_id or f"INC-{matched_alert_id}"
        feedback_entry["fusion_boost_applied"] = True
        feedback_entry["elevated_leak_confidence"] = new_conf
        feedback_entry["matched_device"] = matching_alert.device_id


    FEEDBACK_LOG.append(feedback_entry)
    return feedback_entry


def get_recent_feedback(limit: int = 20) -> List[Dict[str, Any]]:
    """Returns the most recent passenger feedback events."""
    return list(reversed(FEEDBACK_LOG[-limit:]))
