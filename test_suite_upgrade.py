"""Test script to verify WebSocket live endpoint, Executive Reports, and MQTT bridge."""

import asyncio
import json
from fastapi.testclient import TestClient
from app.main import app, STORE
import app.sim as sim

def test_upgrade_suite():
    with TestClient(app) as client:
        print("Testing /api/reports/executive...")
        resp = client.get("/api/reports/executive")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        rep = resp.json()
        assert "report_id" in rep
        assert "audit_hash" in rep
        assert "water_balance" in rep
        assert rep["water_balance"]["total_liters_saved"] >= 0
        print(f"  [PASS] Executive report ID: {rep['report_id']} | Audit: {rep['audit_hash']}")

        print("Testing /api/reports/executive/html...")
        html_resp = client.get("/api/reports/executive/html")
        assert html_resp.status_code == 200
        assert "AquaGuard" in html_resp.text
        assert "OFFICIAL AUDIT LEDGER" in html_resp.text
        print("  [PASS] Executive HTML report rendered successfully")

        print("Testing /api/mqtt/status...")
        mqtt_stat = client.get("/api/mqtt/status")
        assert mqtt_stat.status_code == 200
        stat = mqtt_stat.json()
        assert "supported_topic_template" in stat
        print(f"  [PASS] MQTT template: {stat['supported_topic_template']}")

        print("Testing /api/mqtt/publish...")
        mqtt_payload = {
            "topic": "kohler/facility/pnq/Terminal 2/T2-RR-02/FV-182/telemetry",
            "payload": {
                "device_id": "FV-182",
                "type": "flush_valve",
                "flow_lpm": 2.8,
                "occupancy": False,
                "solenoid_active": False,
                "line_pressure_bar": 2.9,
                "battery_pct": 92
            }
        }
        pub_resp = client.post("/api/mqtt/publish", json=mqtt_payload)
        assert pub_resp.status_code == 200
        pub_data = pub_resp.json()
        assert pub_data["status"] == "ok"
        assert pub_data["device_id"] == "FV-182"
        print(f"  [PASS] MQTT published successfully: device={pub_data['device_id']}")

        print("Testing /ws/live endpoint...")
        with client.websocket_connect("/ws/live") as websocket:
            init_msg = websocket.receive_json()
            assert init_msg["type"] == "init"
            assert "zones" in init_msg["data"]
            assert "facility_health" in init_msg["data"]
            print("  [PASS] WebSocket handshake & init frame received")


            websocket.send_text("ping")
            pong = websocket.receive_text()
            assert pong == "pong"
            print("  [PASS] WebSocket ping/pong responded")

    print("\n======================================")
    print("ALL SUITE UPGRADE TESTS PASSED!")
    print("======================================")

if __name__ == "__main__":
    test_upgrade_suite()
