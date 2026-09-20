"""KOHLER AquaGuard AI — Realistic Edge Hardware MQTT Simulator.

Simulates smart restroom fixtures broadcasting high-frequency MQTT packets
over topics matching `kohler/facility/{airport}/{terminal}/{room}/{device}/telemetry`.
Can publish either via a live MQTT broker (port 1883) or via the AquaGuard HTTP bridge.
"""

import argparse
import json
import random
import time
from datetime import datetime, timezone
import urllib.request

DEVICES = [
    {"id": "FV-182", "type": "flush_valve", "terminal": "Terminal 2", "room": "T2-RR-02", "base_flow": 0.0},
    {"id": "UR-041", "type": "urinal", "terminal": "Terminal 1", "room": "T1-RR-01", "base_flow": 0.0},
    {"id": "FC-098", "type": "faucet", "terminal": "Terminal 3", "room": "T3-RR-01", "base_flow": 0.0},
    {"id": "UR-092", "type": "urinal", "terminal": "Arrivals", "room": "ARR-RR-01", "base_flow": 0.0},
]


def generate_packet(dev: dict, inject_leak: bool = False) -> dict:
    flow = round(random.uniform(2.4, 2.9), 2) if inject_leak else dev["base_flow"]
    occ = random.choice([True, False]) if not inject_leak else False
    solenoid = occ and not inject_leak

    return {
        "device_id": dev["id"],
        "type": dev["type"],
        "flow_lpm": flow,
        "occupancy": occ,
        "solenoid_active": solenoid,
        "line_pressure_bar": round(random.uniform(2.9, 3.1) if not inject_leak else 2.6, 2),
        "battery_pct": random.randint(88, 98),
        "rssi_dbm": random.randint(-72, -58),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def publish_http_bridge(host: str, port: int, topic: str, payload: dict):
    url = f"http://{host}:{port}/api/mqtt/publish"
    req_body = json.dumps({"topic": topic, "payload": payload}).encode("utf-8")
    req = urllib.request.Request(url, data=req_body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as ex:
        print(f"HTTP bridge publish error: {ex}")
        return None


def run_simulator(host: str, port: int, count: int, delay: float, leak_device: str):
    print(f"🚀 Starting KOHLER MQTT Edge Hardware Simulator...")
    print(f"   Target: {host}:{port}")
    print(f"   Devices: {len(DEVICES)}")
    if leak_device:
        print(f"   ⚠️ Injecting simulated leak on device: {leak_device}")

    for i in range(count):
        for dev in DEVICES:
            is_leak = (dev["id"] == leak_device)
            pkt = generate_packet(dev, inject_leak=is_leak)
            topic = f"kohler/facility/pnq/{dev['terminal']}/{dev['room']}/{dev['id']}/telemetry"
            res = publish_http_bridge(host, port, topic, pkt)
            print(f"[{i+1}/{count}] MQTT 📤 {topic} -> Flow: {pkt['flow_lpm']} LPM | Alerts: {res.get('alerts_created', 0) if res else 'Err'}")
            time.sleep(delay)

    print("✅ MQTT Simulation sequence completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KOHLER MQTT Edge Simulator")
    parser.add_argument("--host", default="127.0.0.1", help="AquaGuard server host")
    parser.add_argument("--port", type=int, default=8000, help="AquaGuard server port")
    parser.add_argument("--count", type=int, default=5, help="Number of telemetry loops")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between packets in seconds")
    parser.add_argument("--leak", default="FV-182", help="Device ID to simulate continuous leak on")
    args = parser.parse_args()

    run_simulator(args.host, args.port, args.count, args.delay, args.leak)
