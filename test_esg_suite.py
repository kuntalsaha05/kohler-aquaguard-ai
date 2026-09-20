"""Test suite for ESG, Carbon & Water-Energy Nexus, What-If Stress Testing, and CMMS Work Orders."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_esg_metrics():
    res = client.get("/api/esg/metrics")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "metrics" in data
    assert "co2e_avoided_kg" in data["metrics"]
    assert "energy_saved_kwh" in data["metrics"]
    assert "leed_scorecard" in data
    assert "certificate_id" in data
    assert "sha256_audit_seal" in data
    print(f"  [PASS] ESG metrics verified: {data['metrics']['co2e_avoided_kg']} kg CO2e, {data['metrics']['energy_saved_kwh']} kWh")

def test_what_if_simulation():
    req = {
        "tariff_inr_per_kl": 55.0,
        "pax_growth_pct": 25.0,
        "retrofit_coverage_pct": 100.0
    }
    res = client.post("/api/simulation/what-if", json=req)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "projections" in data
    assert data["projections"]["annual_financial_savings_inr"] > 0
    assert data["projections"]["payback_period_months"] > 0
    print(f"  [PASS] What-If Simulation verified: Payback in {data['projections']['payback_period_months']} months, Annual savings: INR {data['projections']['annual_financial_savings_inr']}")

def test_cmms_work_order():
    res = client.get("/api/cmms/work-order/ALT-00001")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "work_order_number" in data
    assert "required_spare_part" in data
    assert "job_plan_steps" in data
    assert len(data["job_plan_steps"]) > 0
    print(f"  [PASS] CMMS Work Order verified: {data['work_order_number']}, Part: {data['required_spare_part']['part_number']}")

if __name__ == "__main__":
    print("Testing /api/esg/metrics...")
    test_esg_metrics()
    print("Testing /api/simulation/what-if...")
    test_what_if_simulation()
    print("Testing /api/cmms/work-order/{alert_id}...")
    test_cmms_work_order()
    print("\n==========================================")
    print("ALL ESG & CMMS SUITE TESTS PASSED!")
    print("==========================================")
