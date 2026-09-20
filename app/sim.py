"""Digital-twin facility: fleet generation + telemetry simulator.

One tick = one simulated minute of facility operation, emitted every
SIM_INTERVAL_SECONDS (2s) of real time, so the demo compresses hours of
facility time into minutes of wall clock.

Five injectable scenarios mirror the case study:
  continuous-leak | sensor-failure | phantom-flushes | occupancy-spike | device-degradation
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

from .state import (
    LITERS_PER_FLUSH,
    SIM_INTERVAL_SECONDS,
    TICK_MINUTES,
    DeviceState,
    Store,
    TelemetryEvent,
    ZoneState,
    utcnow,
)

rng = random.Random(42)

ZONE_BLUEPRINT = [
    # (zone_id, name, terminal, floor, base_population, cleaning threshold)
    ("Z01", "Terminal 1 — Restroom 02", "Terminal 1", 1, 10, 2600),
    ("Z02", "Terminal 1 — Restroom 03", "Terminal 1", 1, 8, 2600),
    ("Z03", "Terminal 1 — Restroom 07", "Terminal 1", 2, 9, 2600),
    ("Z04", "Terminal 1 — Restroom 11", "Terminal 1", 2, 7, 2600),
    ("Z05", "Terminal 2 — Restroom 14", "Terminal 2", 2, 11, 2600),
    ("Z06", "Terminal 2 — Restroom 18", "Terminal 2", 2, 9, 2600),
    ("Z07", "Terminal 2 — Restroom 22", "Terminal 2", 3, 8, 2600),
    ("Z08", "Terminal 2 — Restroom 26", "Terminal 2", 3, 10, 2600),
    ("Z09", "Terminal 3 — Restroom 31", "Terminal 3", 1, 12, 2600),
    ("Z10", "Terminal 3 — Restroom 35", "Terminal 3", 1, 9, 2600),
    ("Z11", "Terminal 3 — Lounge B",    "Terminal 3", 2, 6, 2600),
    ("Z12", "Arrivals Hall — Restroom 04", "Arrivals", 0, 13, 2600),
]

# hero device ids used in the pitch/demo narrative
HERO_DEVICE = "FV-182"
HERO_ZONE = "Z05"


def seed_hygiene_counters(store: Store) -> None:
    """Lived-in hygiene state, shared by boot and reset so every lifecycle
    path starts from the same baseline (and scenario injection behaves the
    same regardless of when it happens)."""
    for zone in store.zones.values():
        zone.usage_since_cleaning = rng.randint(400, 700)
        zone.last_cleaned_min_ago = rng.randint(90, 300)


def build_fleet(store: Store) -> None:
    """Create the virtual facility: 12 zones, 8 instrumented fixtures each."""
    for zone_id, name, terminal, floor, pop, threshold in ZONE_BLUEPRINT:
        if zone_id not in store.zones:
            store.zones[zone_id] = ZoneState(zone_id, name, terminal, floor, pop, threshold)

    counter = {"fv": 100, "t": 100, "f": 100, "u": 100}

    def next_id(prefix: str) -> str:
        counter[prefix] += 1
        return f"{prefix.upper()}-{counter[prefix]}"

    for zone_id, name, terminal, floor, _pop, _th in ZONE_BLUEPRINT:
        ids = []
        for _ in range(2):
            ids.append(("Flush Valve", "fv", next_id("fv")))
        for _ in range(3):
            ids.append(("Toilet", "t", next_id("t")))
        for _ in range(2):
            ids.append(("Faucet", "f", next_id("f")))
        ids.append(("Urinal Bank", "u", next_id("u")))

        for dtype, prefix, device_id in ids:
            if device_id in store.devices:
                continue
            expected = 2.0 if dtype in ("Flush Valve", "Urinal Bank") else (5.0 if dtype == "Faucet" else 0.0)
            store.devices[device_id] = DeviceState(
                device_id, dtype, zone_id, name, terminal, floor, expected
            )

    # Pin the story device: FV-182 lives in Terminal 2 — Restroom 14
    if HERO_DEVICE not in store.devices:
        store.devices[HERO_DEVICE] = DeviceState(
            HERO_DEVICE, "Flush Valve", HERO_ZONE, "Terminal 2 — Restroom 14", "Terminal 2", 2, 0.0
        )

    seed_hygiene_counters(store)


def _traffic_factor(hour: float) -> float:
    """Airport passenger curve: morning, lunchtime and evening peaks."""
    peaks = [(8.5, 2.2, 1.0), (13.0, 1.8, 0.85), (18.5, 2.2, 0.9)]
    factor = 0.30  # overnight floor keeps the facility alive for demos
    for mu, width, amp in peaks:
        factor += amp * pow(2.718, -((hour - mu) ** 2) / (2 * width * width))
    return min(factor, 1.6)


def _advance_occupancy(store: Store, now) -> None:
    hour = now.hour + now.minute / 60.0
    factor = _traffic_factor(hour)
    for zone in store.zones.values():
        target = round(zone.base_population * factor)
        delta = max(-2, min(2, target - zone.occupancy))
        zone.occupancy = max(0, zone.occupancy + delta + rng.choice((-1, 0, 0, 1)))
        zone.occupancy = max(0, min(zone.occupancy, 40))
        zone.last_cleaned_min_ago += TICK_MINUTES


def _apply_scenarios(store: Store, now) -> None:
    """Mutate scenario state as simulated time advances."""
    sim_now = store.tick_count  # simulated minutes since boot

    leak = store.scenarios.get("continuous-leak")
    if leak and not leak.get("ends_tick") and sim_now - leak["started_tick"] >= 240:
        leak["ends_tick"] = None  # leaks persist until resolved by a human

    spike = store.scenarios.get("occupancy-spike")
    if spike:
        zone = store.zones.get(spike["zone_id"])
        if zone:
            age = sim_now - spike["started_tick"]
            if age < 20:
                zone.occupancy = max(zone.occupancy, int(zone.base_population * 3.2))
            elif age >= 20 and not spike.get("finished"):
                spike["finished"] = True
                spike["ended_at"] = utcnow().isoformat()

    failure = store.scenarios.get("sensor-failure")
    if failure:
        dev = store.devices.get(failure["device_id"])
        if dev:
            dev.sensor_errors += 1
            dev.battery_pct = max(5.0, dev.battery_pct - 1.5)

    degrade = store.scenarios.get("device-degradation")
    if degrade:
        dev = store.devices.get(degrade["device_id"])
        if dev:
            degrade["phase"] = min(10, sim_now - degrade["started_tick"])
            if rng.random() < 0.5:
                dev.sensor_errors += 1  # wearing sensor/actuator


def _normal_device_event(store: Store, dev: DeviceState, now) -> TelemetryEvent:
    zone = store.zones[dev.zone_id]
    flow, flushes, occupancy = 0.0, 0, zone.occupancy

    if dev.type in ("Toilet", "Urinal Bank"):
        # visits scale with current occupancy; each flush ~6 L over ~1 min
        rate = 0.0035 if dev.type == "Toilet" else 0.0045
        if rng.random() < zone.occupancy * rate * 10:
            flushes = 1
            flow = round(rng.uniform(1.6, 2.4), 2) if dev.type == "Urinal Bank" else round(rng.uniform(1.4, 2.2), 2)
    elif dev.type == "Faucet":
        if rng.random() < zone.occupancy * 0.02:
            flow = round(rng.uniform(3.5, 6.0), 2)
    elif dev.type == "Flush Valve":
        # brief supply-line activity when a fixture it serves flushes
        if rng.random() < zone.occupancy * 0.004:
            flow = round(rng.uniform(1.8, 2.5), 2)

    return TelemetryEvent(
        device_id=dev.device_id,
        zone=dev.zone,
        timestamp=now,
        flow_lpm=flow,
        occupancy=occupancy,
        flush_count=flushes,
        expected_flow_lpm=dev.expected_flow_lpm,
        duration_min=1,
        temperature_c=round(rng.uniform(24.0, 29.0), 1),
        sensor_errors=dev.sensor_errors,
        battery_pct=round(dev.battery_pct, 1),
    )


def _scenario_event(store: Store, dev: DeviceState, now, kind: str) -> Optional[TelemetryEvent]:
    sc = store.scenarios.get(kind)
    if not sc:
        return None
    if "devices" in sc:
        if not any(d["device_id"] == dev.device_id for d in sc["devices"]):
            return None
    elif sc.get("device_id") != dev.device_id:
        return None
    zone = store.zones[dev.zone_id]

    if kind == "continuous-leak":
        age = store.tick_count - sc["started_tick"]
        return TelemetryEvent(
            device_id=dev.device_id, zone=dev.zone, timestamp=now,
            flow_lpm=round(2.7 + rng.uniform(-0.08, 0.08), 2),
            occupancy=0, flush_count=0, expected_flow_lpm=0.0,
            duration_min=max(1, age),
            temperature_c=27.0, sensor_errors=0, battery_pct=round(dev.battery_pct, 1),
        )

    if kind == "sensor-failure":
        # frozen occupancy, flatlined/stale flow readings, climbing sensor errors
        stale_flow = sc.get("last_flow", 0.0)
        return TelemetryEvent(
            device_id=dev.device_id, zone=dev.zone, timestamp=now,
            flow_lpm=stale_flow, occupancy=sc.get("frozen_occupancy", 0),
            flush_count=0, expected_flow_lpm=dev.expected_flow_lpm,
            duration_min=1, temperature_c=27.0,
            sensor_errors=dev.sensor_errors,
            battery_pct=round(dev.battery_pct, 1),
        )

    if kind == "phantom-flushes":
        flushes = rng.randint(1, 2)
        flow = round(rng.uniform(1.8, 2.4), 2)
        return TelemetryEvent(
            device_id=dev.device_id, zone=dev.zone, timestamp=now,
            flow_lpm=flow, occupancy=0, flush_count=flushes,
            expected_flow_lpm=dev.expected_flow_lpm, duration_min=1,
            temperature_c=27.0, sensor_errors=0, battery_pct=round(dev.battery_pct, 1),
        )

    if kind == "device-degradation":
        # Wearing fixture: intermittent micro-flows while idle that grow more
        # frequent and larger as wear progresses (a degrading seal opens
        # progressively), plus accumulating sensor noise — this is what drives
        # the health model into HIGH risk before a sustained leak develops.
        phase = int(sc.get("phase", 0))
        flow = 0.0
        if rng.random() < 0.35 + phase * 0.05:
            flow = round(rng.uniform(0.3, 0.5 + phase * 0.12), 2)
        return TelemetryEvent(
            device_id=dev.device_id, zone=dev.zone, timestamp=now,
            flow_lpm=flow, occupancy=0, flush_count=0,
            expected_flow_lpm=0.0, duration_min=1,
            temperature_c=27.0, sensor_errors=dev.sensor_errors,
            battery_pct=round(dev.battery_pct, 1),
        )

    if kind == "pressure-anomaly":
        age = store.tick_count - sc["started_tick"]
        return TelemetryEvent(
            device_id=dev.device_id, zone=dev.zone, timestamp=now,
            flow_lpm=round(3.4 + rng.uniform(-0.1, 0.1), 2),
            occupancy=0, flush_count=0, expected_flow_lpm=0.0,
            duration_min=max(1, age),
            temperature_c=26.0, sensor_errors=1, battery_pct=round(dev.battery_pct, 1),
        )

    if kind == "multiple-leaks":
        devices_dict = {d["device_id"]: d["flow_lpm"] for d in sc.get("devices", [])}
        flow = devices_dict.get(dev.device_id, 2.0)
        age = store.tick_count - sc["started_tick"]
        return TelemetryEvent(
            device_id=dev.device_id, zone=dev.zone, timestamp=now,
            flow_lpm=round(flow + rng.uniform(-0.05, 0.05), 2),
            occupancy=0, flush_count=0, expected_flow_lpm=0.0,
            duration_min=max(1, age),
            temperature_c=26.5, sensor_errors=0, battery_pct=round(dev.battery_pct, 1),
        )

    return None


def generate_tick(store: Store) -> List[TelemetryEvent]:
    """Produce one telemetry tick for the whole fleet.

    Devices whose writer slot is held by an external /telemetry stream are
    skipped — one writer per device at a time (see engine.process_events).
    """
    now = utcnow()
    _advance_occupancy(store, now)
    _apply_scenarios(store, now)

    events: List[TelemetryEvent] = []
    active_devices = set()
    for sc in store.scenarios.values():
        if sc.get("device_id") and not sc.get("finished"):
            active_devices.add(sc["device_id"])
        if sc.get("devices"):
            for d_item in sc["devices"]:
                active_devices.add(d_item["device_id"])

    for dev in store.devices.values():
        if dev.device_id in store.hold_writers:
            continue  # external stream owns this device's writer slot
        if dev.device_id in active_devices:
            for kind in store.scenarios:
                ev = _scenario_event(store, dev, now, kind)
                if ev:
                    events.append(ev)
                    if kind == "sensor-failure":
                        store.scenarios[kind]["last_flow"] = ev.flow_lpm
                    break
            continue
        events.append(_normal_device_event(store, dev, now))

    store.tick_count += TICK_MINUTES
    return events


# ---------------- scenario control ----------------

def _pick_device(store: Store, kinds: List[str], prefer: Optional[str] = None) -> DeviceState:
    if not store.devices:
        build_fleet(store)
    if prefer and prefer in store.devices:
        return store.devices[prefer]
    candidates = [d for d in store.devices.values() if d.type in kinds]
    return rng.choice(candidates) if candidates else next(iter(store.devices.values()))


SCENARIO_META = {
    "continuous-leak": {
        "label": "Continuous leak",
        "device_types": ["Flush Valve"],
        "prefer": HERO_DEVICE,
        "narrative": "Flush valve stuck open — flow with zero occupancy and zero flushes",
    },
    "sensor-failure": {
        "label": "Sensor failure",
        "device_types": ["Faucet", "Urinal Bank"],
        "narrative": "Telemetry flatline with frozen occupancy and climbing sensor errors",
    },
    "phantom-flushes": {
        "label": "Phantom flushes",
        "device_types": ["Toilet"],
        "narrative": "Flush events firing with zero occupancy — solenoid/valve fault",
    },
    "occupancy-spike": {
        "label": "Occupancy spike",
        "device_types": [],
        "narrative": "Sudden crowd surge — hygiene usage rate triples",
    },
    "device-degradation": {
        "label": "Device degradation",
        "device_types": ["Flush Valve"],
        "narrative": "Progressive wear — intermittent idle micro-flows and sensor noise",
    },
    "pressure-anomaly": {
        "label": "Pressure drop",
        "device_types": ["Flush Valve"],
        "prefer": "FV-105",
        "narrative": "Supply line pressure drop from 3.2 bar to 1.2 bar with 3.4 L/min surge",
    },
    "multiple-leaks": {
        "label": "Multi-leak storm",
        "device_types": [],
        "narrative": "Concurrent leaks across terminals to test automated P1/P2/P3 prioritization",
    },
}


def start_scenario(store: Store, kind: str, device_id: Optional[str] = None) -> dict:
    meta = SCENARIO_META.get(kind)
    if not meta:
        raise ValueError(f"unknown scenario '{kind}'")

    if kind == "occupancy-spike":
        zone_id = device_id if device_id in store.zones else HERO_ZONE
        store.scenarios[kind] = {
            "zone_id": zone_id, "started_tick": store.tick_count,
            "label": meta["label"], "narrative": meta["narrative"],
            "usage_mult": 12.0,  # crowd surge: far more people × heavier per-person usage
        }
        return {"scenario": kind, "zone_id": zone_id,
                "zone": store.zones[zone_id].name}

    if kind == "multiple-leaks":
        store.scenarios[kind] = {
            "started_tick": store.tick_count,
            "label": meta["label"],
            "narrative": meta["narrative"],
            "devices": [
                {"device_id": "FV-182", "flow_lpm": 2.7},  # P1 Critical
                {"device_id": "FV-105", "flow_lpm": 1.5},  # P2 High
                {"device_id": "T-128",  "flow_lpm": 0.7},  # P3 Medium
            ]
        }
        return {
            "scenario": kind,
            "devices_count": 3,
            "targets": ["FV-182 (P1)", "FV-105 (P2)", "T-128 (P3)"],
            "narrative": meta["narrative"],
        }

    dev = _pick_device(store, meta["device_types"], device_id or meta.get("prefer"))
    if kind == "sensor-failure":
        store.scenarios[kind] = {
            "device_id": dev.device_id, "started_tick": store.tick_count,
            "frozen_occupancy": store.zones[dev.zone_id].occupancy,
            "last_flow": 0.0, "label": meta["label"], "narrative": meta["narrative"],
        }
    else:
        store.scenarios[kind] = {
            "device_id": dev.device_id, "started_tick": store.tick_count,
            "phase": 0, "label": meta["label"], "narrative": meta["narrative"],
        }
    return {"scenario": kind, "device_id": dev.device_id,
            "zone": dev.zone, "device_type": dev.type}


def stop_all_scenarios(store: Store) -> None:
    store.scenarios.clear()
