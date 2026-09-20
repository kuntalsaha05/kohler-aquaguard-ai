"""KOHLER AquaGuard AI — Acoustic Hydrophone Audio Diagnostics Engine.

Generates acoustic frequency profiles, cavitation flutter rates, and total
harmonic distortion (THD) parameters for smart restroom fixtures based on
hydraulic pressure, flow turbulence, and physical failure modes.
"""

from typing import Any, Dict

ACOUSTIC_PROFILES = {
    "nominal": {
        "timbre": "Laminar Fluid Flow",
        "fundamental_freq_hz": 420.0,
        "secondary_freq_hz": 840.0,
        "cavitation_flutter_hz": 0.0,
        "thd_percent": 2.1,
        "amplitude": 0.22,
        "waveform": "sine",
        "noise_type": "pink",
        "description": "Smooth laminar flow through aerator and brass orifice. Low acoustic intensity, no structural pipe cavitation."
    },
    "diaphragm_tear": {
        "timbre": "High-Frequency Cavitation Screech",
        "fundamental_freq_hz": 2420.0,
        "secondary_freq_hz": 4840.0,
        "cavitation_flutter_hz": 14.5,
        "thd_percent": 38.4,
        "amplitude": 0.88,
        "waveform": "sawtooth",
        "noise_type": "white",
        "description": "Severe acoustic whistling caused by high-velocity water jetting across torn EPDM diaphragm bypass orifice under 3.0 bar pressure."
    },
    "solenoid_cycling": {
        "timbre": "Pulsed Solenoid Chatter & Water Hammer",
        "fundamental_freq_hz": 120.0,
        "secondary_freq_hz": 240.0,
        "cavitation_flutter_hz": 4.0,
        "thd_percent": 24.6,
        "amplitude": 0.65,
        "waveform": "square",
        "noise_type": "brown",
        "description": "Rattling valve core due to bi-stable solenoid actuator failure. Rapid pressure fluctuations inducing mechanical chatter."
    },
    "pressure_surge": {
        "timbre": "Low-Frequency Riser Resonance",
        "fundamental_freq_hz": 85.0,
        "secondary_freq_hz": 170.0,
        "cavitation_flutter_hz": 2.5,
        "thd_percent": 18.2,
        "amplitude": 0.72,
        "waveform": "triangle",
        "noise_type": "pink",
        "description": "Acoustic resonance across airport terminal risers caused by supply pressure oscillations."
    },
    "silent": {
        "timbre": "Quiescent Static Baseline",
        "fundamental_freq_hz": 0.0,
        "secondary_freq_hz": 0.0,
        "cavitation_flutter_hz": 0.0,
        "thd_percent": 0.0,
        "amplitude": 0.02,
        "waveform": "sine",
        "noise_type": "none",
        "description": "Zero active flow. Ambient sensor electronic thermal floor noise."
    }
}


def get_fixture_acoustic_profile(dev_id: str, store) -> Dict[str, Any]:
    """Generates the real-time acoustic hydrophone profile for a fixture."""
    dev = store.devices.get(dev_id)
    if not dev:
        profile = ACOUSTIC_PROFILES["silent"].copy()
        profile["device_id"] = dev_id
        return profile

    # Check for active alert
    alert = next((a for a in store.alerts if a.device_id == dev_id and a.status == "OPEN"), None)
    flow = getattr(dev, "flow_lpm", 0.0)

    if alert:
        cause = getattr(alert, "root_cause", "")
        if "Diaphragm" in cause or "Leak" in alert.kind:
            profile = ACOUSTIC_PROFILES["diaphragm_tear"].copy()
        elif "Solenoid" in cause or "Phantom" in alert.kind:
            profile = ACOUSTIC_PROFILES["solenoid_cycling"].copy()
        elif "Pressure" in cause:
            profile = ACOUSTIC_PROFILES["pressure_surge"].copy()
        else:
            profile = ACOUSTIC_PROFILES["diaphragm_tear"].copy()
    elif flow > 0.5:
        profile = ACOUSTIC_PROFILES["nominal"].copy()
    else:
        profile = ACOUSTIC_PROFILES["silent"].copy()

    profile["device_id"] = dev_id
    profile["flow_lpm"] = round(flow, 2)
    profile["pressure_bar"] = round(getattr(dev, "pressure_bar", 3.0), 2)
    profile["zone"] = dev.zone
    return profile
