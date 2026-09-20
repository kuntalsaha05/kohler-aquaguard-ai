"""Test suite to verify Acoustic Audio Diagnostics and Multi-Airport Portfolio."""

from fastapi.testclient import TestClient
from app.main import app, STORE

def test_innovation_pack():
    with TestClient(app) as client:
        print("Testing /api/audio/profile/{device_id}...")
        res = client.get("/api/audio/profile/FV-182")
        assert res.status_code == 200
        audio = res.json()
        assert "fundamental_freq_hz" in audio
        assert "thd_percent" in audio
        assert "timbre" in audio
        print(f"  [PASS] Acoustic audio profile: {audio['timbre']} ({audio['fundamental_freq_hz']} Hz)")

        print("Testing /api/portfolio/airports...")
        res = client.get("/api/portfolio/airports")
        assert res.status_code == 200
        aps = res.json()["airports"]
        assert len(aps) == 3
        codes = [a["airport_code"] for a in aps]
        assert "PNQ" in codes and "BOM" in codes and "DEL" in codes
        print(f"  [PASS] Airport list: {codes}")

        print("Testing /api/portfolio/summary...")
        res = client.get("/api/portfolio/summary")
        assert res.status_code == 200
        summ = res.json()
        assert "total_monitored_fixtures" in summ
        assert summ["total_monitored_fixtures"] >= 590
        assert "consolidated_daily_water_saved_liters" in summ
        print(f"  [PASS] Portfolio summary: {summ['total_monitored_fixtures']} fixtures, {summ['consolidated_daily_water_saved_liters']} L/day saved")

    print("\n==========================================")
    print("ALL INNOVATION PACK TESTS PASSED!")
    print("==========================================")

if __name__ == "__main__":
    test_innovation_pack()
