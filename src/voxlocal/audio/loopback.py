"""System loopback speaker audio stream reader."""

import logging
import threading
from collections.abc import Callable

import numpy as np
import soundcard as sc

from voxlocal.audio.device import get_default_devices
from voxlocal.audio.resampler import resample_audio, to_mono

logger = logging.getLogger(__name__)


class LoopbackStreamReader:
    """Captures system output audio (speakers / meeting participants) via WASAPI loopback."""

    def __init__(
        self,
        device_name_or_id: str | None = None,
        target_sr: int = 16000,
        block_size: int = 2048,
        callback: Callable[[np.ndarray, float], None] | None = None,
    ):
        """Initialize loopback reader.

        Args:
            device_name_or_id: Loopback device name or ID substring, or None for default.
            target_sr: Target sample rate in Hz (default 16000).
            block_size: Frame size read per chunk from hardware.
            callback: Function called when new resampled audio chunk is available:
                      callback(samples: np.ndarray, rms: float).
        """
        self.device_name_or_id = device_name_or_id
        self.target_sr = target_sr
        self.block_size = block_size
        self.callback = callback
        self._running = False
        self._thread: threading.Thread | None = None
        self._device = self._resolve_device()

    def _resolve_device(self):
        """Locate WASAPI loopback device."""
        all_mics = sc.all_microphones(include_loopback=True)
        loopbacks = [m for m in all_mics if getattr(m, "isloopback", False)]

        if self.device_name_or_id:
            for lb in loopbacks:
                if self.device_name_or_id.lower() in lb.name.lower() or self.device_name_or_id in str(lb.id):
                    return lb

        _, default_loopback = get_default_devices()
        if default_loopback is not None:
            return default_loopback

        if loopbacks:
            return loopbacks[0]
        return None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def device_name(self) -> str:
        return self._device.name if self._device else "No loopback device detected"

    def start(self) -> None:
        """Start loopback recording thread."""
        if self._running:
            return
        if self._device is None:
            logger.warning("No loopback device available to start.")
            return

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="LoopbackCaptureThread")
        self._thread.start()
        logger.info("Loopback capture started on device: %s", self.device_name)

    def stop(self) -> None:
        """Stop loopback recording thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        logger.info("Loopback capture stopped.")

    def _capture_loop(self) -> None:
        """Internal loopback reading loop."""
        native_sr = 48000
        try:
            with self._device.recorder(samplerate=native_sr, blocksize=self.block_size) as recorder:
                while self._running:
                    data = recorder.record(numframes=self.block_size)
                    if data is None or len(data) == 0:
                        continue
                    mono = to_mono(data)
                    resampled = resample_audio(mono, orig_sr=native_sr, target_sr=self.target_sr)
                    rms = float(np.sqrt(np.mean(np.square(resampled))))
                    if self.callback:
                        self.callback(resampled, rms)
        except Exception as exc:
            logger.error("Error in loopback capture loop: %s", exc)
            self._running = False
