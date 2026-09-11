"""Audio device discovery and hardware selection utilities."""


import logging
import warnings

import soundcard as sc

warnings.filterwarnings("ignore", message=".*data discontinuity in recording.*")

logger = logging.getLogger(__name__)


def list_microphones() -> list[dict[str, str]]:
    """List available input microphones (excluding loopback devices)."""
    devices = []
    try:
        mics = sc.all_microphones(include_loopback=False)
        for idx, mic in enumerate(mics):
            devices.append({
                "index": str(idx),
                "id": str(mic.id),
                "name": mic.name,
                "channels": str(mic.channels),
            })
    except Exception as exc:
        devices.append({"index": "0", "id": "fallback", "name": f"Error querying mics: {exc}", "channels": "1"})
    return devices


def list_loopback_devices() -> list[dict[str, str]]:
    """List available loopback devices for capturing system speaker audio."""
    devices = []
    try:
        all_mics = sc.all_microphones(include_loopback=True)
        loopbacks = [m for m in all_mics if getattr(m, "isloopback", False)]
        for idx, lb in enumerate(loopbacks):
            devices.append({
                "index": str(idx),
                "id": str(lb.id),
                "name": lb.name,
                "channels": str(lb.channels),
            })
    except Exception as exc:
        devices.append({"index": "0", "id": "fallback", "name": f"Error querying loopback: {exc}", "channels": "2"})
    return devices


def get_default_devices() -> tuple[sc.default_microphone | None, sc.default_speaker | None]:
    """Retrieve default input microphone and default loopback speaker."""
    mic = None
    loopback = None
    try:
        mic = sc.default_microphone()
    except Exception as exc:
        logger.debug("Could not get default microphone: %s", exc)

    try:
        # On Windows WASAPI, the loopback device is obtained via get_microphone(id, include_loopback=True)
        # or from default_speaker().
        speaker = sc.default_speaker()
        if speaker is not None:
            # Soundcard allows matching loopback microphone by speaker id or name
            all_mics = sc.all_microphones(include_loopback=True)
            for m in all_mics:
                if getattr(m, "isloopback", False) and (m.name == speaker.name or m.id == speaker.id):
                    loopback = m
                    break
            if loopback is None:
                # Fallback to first loopback device found
                lbs = [m for m in all_mics if getattr(m, "isloopback", False)]
                if lbs:
                    loopback = lbs[0]
    except Exception as exc:
        logger.debug("Could not get default loopback speaker: %s", exc)

    return mic, loopback
