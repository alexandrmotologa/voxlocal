"""Microphone audio stream reader."""

import logging
import threading
from collections.abc import Callable

import numpy as np
import soundcard as sc

from voxlocal.audio.device import get_default_devices
from voxlocal.audio.resampler import resample_audio, to_mono

logger = logging.getLogger(__name__)


class MicStreamReader:
    """Captures audio from the local input microphone on a dedicated thread."""

    def __init__(
        self,
        device_name_or_id: str | None = None,
        target_sr: int = 16000,
        block_size: int = 2048,
        callback: Callable[[np.ndarray, float], None] | None = None,
    ):
        """Initialize microphone reader.

        Args:
            device_name_or_id: Device name or ID substring, or None for default.
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
        """Locate microphone device."""
        if self.device_name_or_id:
            all_mics = sc.all_microphones(include_loopback=False)
            for m in all_mics:
                if self.device_name_or_id.lower() in m.name.lower() or self.device_name_or_id in str(m.id):
                    return m
        default_mic, _ = get_default_devices()
        return default_mic

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def device_name(self) -> str:
        return self._device.name if self._device else "No microphone detected"

    def start(self) -> None:
        """Start microphone recording thread."""
        if self._running:
            return
        if self._device is None:
            logger.warning("No microphone device available to start.")
            return

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="MicCaptureThread")
        self._thread.start()
        logger.info("Microphone capture started on device: %s", self.device_name)

    def stop(self) -> None:
        """Stop microphone recording thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        logger.info("Microphone capture stopped.")

    def _capture_loop(self) -> None:
        """Internal audio reading loop."""
        native_sr = 48000
        try:
            with self._device.recorder(samplerate=native_sr, blocksize=self.block_size) as recorder:
                while self._running:
                    data = recorder.record(numframes=self.block_size)
                    if data is None or len(data) == 0:
                        continue
                    # Convert to mono float32
                    mono = to_mono(data)
                    # Resample to 16kHz
                    resampled = resample_audio(mono, orig_sr=native_sr, target_sr=self.target_sr)
                    rms = float(np.sqrt(np.mean(np.square(resampled))))
                    if self.callback:
                        self.callback(resampled, rms)
        except Exception as exc:
            logger.error("Error in microphone capture loop: %s", exc)
            self._running = False
