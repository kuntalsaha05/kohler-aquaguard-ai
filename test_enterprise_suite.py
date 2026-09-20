"""Test suite to verify Kohler OEM Spares, Predictive Lifecycle, Passenger QR Feedback, and Dispatch Webhooks."""

from fastapi.testclient import TestClient
from app.main import app, STORE

def test_enterprise_capabilities():
    with TestClient(app) as client:
        print("Testing /mobile route...")
        res = client.get("/mobile")
        assert res.status_code == 200
        assert "AQUAGUARD" in res.text
        assert "FIELDOPS" in res.text
        print("  [PASS] Mobile console HTML served")

        print("Testing /api/spares/catalog...")
        res = client.get("/api/spares/catalog")
        assert res.status_code == 200
        catalog = res.json()["catalog"]
        assert "KOHLER-GP1138930" in catalog
        assert catalog["KOHLER-GP1138930"]["unit_cost_inr"] == 1850.0
        print("  [PASS] Kohler OEM catalog verified")

        print("Testing /api/spares/inventory...")
        res = client.get("/api/spares/inventory")
        assert res.status_code == 200
        inv = res.json()
        assert "Terminal 2 Central Maintenance Depot" in inv["depots"]
        print("  [PASS] Depot inventory verified")

        print("Testing /api/spares/requisition...")
        req_body = {
            "incident_id": "INC-TEST-001",
            "device_id": "FV-182",
            "part_number": "KOHLER-GP1138930",
            "quantity": 2,
            "depot": "Terminal 2 Central Maintenance Depot",
            "technician": "Priya Sharma",
            "urgency": "P1 Urgent"
        }
        res = client.post("/api/spares/requisition", json=req_body)
        assert res.status_code == 200
        req_data = res.json()
        assert req_data["part_number"] == "KOHLER-GP1138930"
        assert req_data["quantity"] == 2
        assert req_data["status"] == "ALLOCATED"
        print(f"  [PASS] Requisition created: {req_data['requisition_id']}")

        print("Testing /api/lifecycle/fleet...")
        res = client.get("/api/lifecycle/fleet")
        assert res.status_code == 200
        fleet = res.json()["fleet_lifecycle"]
        assert len(fleet) > 0
        sample = fleet[0]
        assert "cycle_wear_pct" in sample
        assert "trajectory_7d" in sample
        assert len(sample["trajectory_7d"]) == 8
        print(f"  [PASS] Fleet lifecycle calculated ({len(fleet)} assets)")

        print("Testing /api/lifecycle/predictions...")
        res = client.get("/api/lifecycle/predictions")
        assert res.status_code == 200
        preds = res.json()
        assert "total_monitored_assets" in preds
        assert "proactive_cost_savings_inr" in preds
        print(f"  [PASS] Predictive overview: {preds['total_monitored_assets']} assets, {preds['average_fleet_wear_pct']}% avg wear")

        print("Testing /api/feedback (Passenger QR Ingestion & Fusion)...")
        # First inject an alert on FV-182
        sim_res = client.post("/simulate/continuous-leak?device_id=FV-182").json()
        target_dev = sim_res.get("device_id", "FV-182")
        from app import sim, engine
        for _ in range(6):
            events = sim.generate_tick(STORE)
            engine.process_events(STORE, events)

        fb_body = {
            "restroom_id": "T2-RR-02",
            "issue_category": "running_toilet",
            "rating": 1,
            "stall_number": "Stall 4",
            "device_id": target_dev,
            "comment": "Water continuously running into the toilet bowl",
            "passenger_flight": "AI-852"
        }
        res = client.post("/api/feedback", json=fb_body)
        assert res.status_code == 200
        fb_data = res.json()
        assert fb_data["fusion_boost_applied"] is True
        assert fb_data["matched_device"] == target_dev

        assert fb_data["elevated_leak_confidence"] > 0.85
        print(f"  [PASS] Passenger QR feedback fused: elevated confidence to {fb_data['elevated_leak_confidence']:.0%}")

        print("Testing /api/notifications/test-dispatch & dispatch-log...")
        disp_req = {
            "incident_id": "INC-ALT-00018",
            "device_id": "FV-182",
            "zone": "Terminal 2 · Restroom T2-RR-02",
            "priority": "P1",
            "root_cause": "Flush Valve Diaphragm Tear",
            "oem_part": "KOHLER-GP1138930",
            "stock_location": "T2 Depot Rack B-04",
            "technician": "Priya Sharma",
            "sla_minutes": 15
        }
        res = client.post("/api/notifications/test-dispatch", json=disp_req)
        assert res.status_code == 200
        disp_data = res.json()
        assert disp_data["transmission_status"] == "DELIVERED"
        assert disp_data["technician"] == "Priya Sharma"

        res_log = client.get("/api/notifications/dispatch-log")
        assert res_log.status_code == 200
        log = res_log.json()
        assert len(log) > 0
        print(f"  [PASS] Dispatch alert transmitted via CAD: {disp_data['dispatch_id']}")

    print("\n==========================================")
    print("ALL QUAD ENTERPRISE SUITE TESTS PASSED!")
    print("==========================================")

if __name__ == "__main__":
    test_enterprise_capabilities()
