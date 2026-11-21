"""Audio device discovery and hardware selection utilities."""

from __future__ import annotations

import logging
import warnings
from typing import Any

warnings.filterwarnings("ignore", message=".*data discontinuity in recording.*")

logger = logging.getLogger(__name__)

try:
    import soundcard as sc
except Exception as exc:
    sc = None
    logger.warning("Could not initialize soundcard backend: %s", exc)


def list_microphones() -> list[dict[str, str]]:
    """List available input microphones (excluding loopback devices)."""
    if sc is None:
        return [{"index": "0", "id": "mock", "name": "Mock Microphone (Headless)", "channels": "1"}]
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
    if sc is None:
        return [{"index": "0", "id": "mock-loopback", "name": "Mock Loopback (Headless)", "channels": "2"}]
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


def get_default_devices() -> tuple[Any, Any]:
    """Retrieve default input microphone and default loopback speaker."""
    if sc is None:
        return None, None
    mic = None
    loopback = None
    try:
        mic = sc.default_microphone()
    except Exception as exc:
        logger.debug("Could not get default microphone: %s", exc)

    try:
        # On Windows WASAPI, the loopback device is obtained via get_microphone(id, include_loopback=True)
        # or from default_speaker().
        all_mics = sc.all_microphones(include_loopback=True)
        loopbacks = [m for m in all_mics if getattr(m, "isloopback", False)]
        if loopbacks:
            loopback = loopbacks[0]
        else:
            loopback = sc.default_speaker()
    except Exception as exc:
        logger.debug("Could not get default loopback/speaker: %s", exc)

    return mic, loopback
