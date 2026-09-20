"""KOHLER AquaGuard AI — MQTT Edge Ingestion Bridge.

Provides production MQTT protocol support for smart fixtures, solenoid valves,
and water pressure transponders across airport terminals.

Supported Topic Structure:
    kohler/facility/{airport_id}/{terminal}/{restroom}/{device_id}/telemetry
    e.g. kohler/facility/pnq/Terminal 2/T2-RR-02/FV-182/telemetry

Payload Format (JSON):
    {
        "device_id": "FV-182",
        "type": "flush_valve",
        "flow_lpm": 2.7,
        "occupancy": false,
        "solenoid_active": false,
        "line_pressure_bar": 2.95,
        "battery_pct": 92,
        "rssi_dbm": -65,
        "timestamp": "2026-09-20T16:20:00Z"
    }
"""

import json
import logging
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
from app.state import TelemetryEvent
from app import engine

logger = logging.getLogger("aquaguard.mqtt")

# Topic parser pattern
TOPIC_REGEX = re.compile(r"^kohler/facility/([^/]+)/([^/]+)/([^/]+)/([^/]+)/telemetry$")


class MQTTBridge:
    """Manages MQTT ingestion, topic parsing, and telemetry pipeline routing."""

    def __init__(self, store):
        self.store = store
        self.messages_received: int = 0
        self.last_message_at: Optional[str] = None
        self.last_topic: Optional[str] = None
        self.client = None
        self.is_connected: bool = False
        self.broker_host: Optional[str] = None
        self.broker_port: Optional[int] = None

    def parse_topic(self, topic: str) -> Optional[Dict[str, str]]:
        """Extracts facility hierarchy from the topic."""
        m = TOPIC_REGEX.match(topic)
        if not m:
            return None
        return {
            "airport_id": m.group(1),
            "terminal": m.group(2),
            "restroom": m.group(3),
            "device_id": m.group(4),
        }

    def ingest_payload(self, topic: str, payload_bytes: bytes) -> Dict[str, Any]:
        """Parses an MQTT payload, constructs a TelemetryEvent, and feeds the engine."""
        self.messages_received += 1
        self.last_topic = topic
        self.last_message_at = datetime.now(timezone.utc).isoformat()

        meta = self.parse_topic(topic)
        try:
            raw = json.loads(payload_bytes.decode("utf-8"))
        except Exception as ex:
            logger.warning(f"Failed to decode MQTT JSON payload on {topic}: {ex}")
            return {"status": "error", "error": f"JSON decode failure: {ex}"}

        dev_id = raw.get("device_id") or (meta["device_id"] if meta else "UNKNOWN")
        device = self.store.devices.get(dev_id)
        zone = raw.get("zone") or (device.zone if device else (meta["restroom"] if meta else "T2-RR-02"))
        flow = float(raw.get("flow_lpm", 0.0))
        occupancy_val = 1 if raw.get("occupancy") else 0
        flush_count_val = int(raw.get("flush_count", 1 if raw.get("solenoid_active") else 0))

        # Build standard TelemetryEvent
        event = TelemetryEvent(
            device_id=dev_id,
            zone=zone,
            flow_lpm=flow,
            occupancy=occupancy_val,
            flush_count=flush_count_val,
        )

        # Process through detection engine with external writer priority
        result = engine.process_events(self.store, [event], external=True)

        return {
            "status": "ok",
            "device_id": dev_id,
            "topic": topic,
            "alerts_created": len(result.get("new_alerts", [])),
            "tickets_created": len(result.get("new_tickets", [])),
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_connected": self.is_connected,
            "broker_host": self.broker_host or "None (Standby)",
            "broker_port": self.broker_port or 1883,
            "messages_received": self.messages_received,
            "last_message_at": self.last_message_at,
            "last_topic": self.last_topic,
            "supported_topic_template": "kohler/facility/{airport_id}/{terminal}/{restroom}/{device_id}/telemetry",
        }


# Global bridge singleton instantiated by main.py
BRIDGE: Optional[MQTTBridge] = None


def get_bridge(store) -> MQTTBridge:
    global BRIDGE
    if BRIDGE is None:
        BRIDGE = MQTTBridge(store)
    return BRIDGE
