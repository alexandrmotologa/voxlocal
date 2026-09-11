"""Dual-channel audio synchronizer and mixer with hardware speaker tracking."""

import queue
import time
from dataclasses import dataclass
from typing import Literal

import numpy as np

from voxlocal.audio.resampler import calculate_rms, normalize_audio


@dataclass
class AudioFrame:
    """Synchronized audio buffer with speaker channel attribution."""

    data: np.ndarray
    channel_source: Literal["mic", "loopback", "mixed"]
    mic_rms: float
    loopback_rms: float
    timestamp: float


class DualChannelAudioMixer:
    """Synchronizes and mixes microphone (local) and loopback (remote) audio streams."""

    def __init__(
        self,
        target_sr: int = 16000,
        frame_samples: int = 512,  # 32ms frame at 16kHz
        queue_maxsize: int = 200,
    ):
        self.target_sr = target_sr
        self.frame_samples = frame_samples
        self.frame_queue: queue.Queue[AudioFrame] = queue.Queue(maxsize=queue_maxsize)

        self._mic_buffer = np.zeros(0, dtype=np.float32)
        self._loopback_buffer = np.zeros(0, dtype=np.float32)

        self._latest_mic_rms: float = 0.0
        self._latest_loopback_rms: float = 0.0

    @property
    def current_rms_levels(self) -> tuple[float, float]:
        """Return (mic_rms, loopback_rms) for live VU meters."""
        return self._latest_mic_rms, self._latest_loopback_rms

    def on_mic_data(self, samples: np.ndarray, rms: float) -> None:
        """Callback for incoming microphone audio."""
        self._latest_mic_rms = rms
        self._mic_buffer = np.concatenate((self._mic_buffer, samples))
        self._process_buffers()

    def on_loopback_data(self, samples: np.ndarray, rms: float) -> None:
        """Callback for incoming loopback speaker audio."""
        self._latest_loopback_rms = rms
        self._loopback_buffer = np.concatenate((self._loopback_buffer, samples))
        self._process_buffers()

    def _process_buffers(self) -> None:
        """Extract synchronized frames of length frame_samples from buffers."""
        while (
            len(self._mic_buffer) >= self.frame_samples
            and len(self._loopback_buffer) >= self.frame_samples
        ):
            mic_chunk = self._mic_buffer[: self.frame_samples]
            self._mic_buffer = self._mic_buffer[self.frame_samples :]

            loopback_chunk = self._loopback_buffer[: self.frame_samples]
            self._loopback_buffer = self._loopback_buffer[self.frame_samples :]

            mic_chunk_rms = calculate_rms(mic_chunk)
            loopback_chunk_rms = calculate_rms(loopback_chunk)

            # Determine dominant channel
            if mic_chunk_rms > 0.01 and loopback_chunk_rms <= 0.005:
                source: Literal["mic", "loopback", "mixed"] = "mic"
                mixed_data = mic_chunk
            elif loopback_chunk_rms > 0.01 and mic_chunk_rms <= 0.005:
                source = "loopback"
                mixed_data = loopback_chunk
            elif mic_chunk_rms > 0.01 and loopback_chunk_rms > 0.01:
                source = "mixed"
                # Combine both streams and normalize
                combined = mic_chunk + loopback_chunk
                mixed_data = normalize_audio(combined)
            else:
                # Silence or ambient noise: pick highest
                source = "mic" if mic_chunk_rms >= loopback_chunk_rms else "loopback"
                mixed_data = mic_chunk if source == "mic" else loopback_chunk

            frame = AudioFrame(
                data=mixed_data,
                channel_source=source,
                mic_rms=mic_chunk_rms,
                loopback_rms=loopback_chunk_rms,
                timestamp=time.time(),
            )

            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                # Drop oldest frame to maintain real-time latency
                try:
                    self.frame_queue.get_nowait()
                    self.frame_queue.put_nowait(frame)
                except (queue.Empty, queue.Full):
                    pass

    def pull_frame(self, timeout: float = 0.05) -> AudioFrame | None:
        """Pull the next synchronized audio frame from the queue."""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def clear(self) -> None:
        """Reset internal buffers and queue."""
        self._mic_buffer = np.zeros(0, dtype=np.float32)
        self._loopback_buffer = np.zeros(0, dtype=np.float32)
        with self.frame_queue.mutex:
            self.frame_queue.queue.clear()
