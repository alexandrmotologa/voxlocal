"""Silero Voice Activity Detection (VAD) filter."""

import logging
from dataclasses import dataclass

import numpy as np

try:
    from faster_whisper.vad import VadOptions, get_speech_timestamps, get_vad_model
    _HAS_SILERO = True
except ImportError:
    _HAS_SILERO = False

from voxlocal.audio.resampler import calculate_rms

logger = logging.getLogger(__name__)


@dataclass
class SpeechSegment:
    """Represents an active speech segment in audio buffer."""

    start_sample: int
    end_sample: int
    start_sec: float
    end_sec: float


class VoiceActivityDetector:
    """Detects human speech activity using Silero VAD with energy fallback."""

    def __init__(
        self,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 300,
        speech_pad_ms: int = 200,
        sample_rate: int = 16000,
        mode: str = "auto",  # "auto", "silero", "energy"
    ):
        self.threshold = threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms
        self.speech_pad_ms = speech_pad_ms
        self.sample_rate = sample_rate
        self.mode = mode

        self._silero_model = None
        self._vad_options = None

        if _HAS_SILERO and mode in ("auto", "silero"):
            try:
                self._silero_model = get_vad_model()
                self._vad_options = VadOptions(
                    threshold=self.threshold,
                    min_speech_duration_ms=self.min_speech_duration_ms,
                    min_silence_duration_ms=self.min_silence_duration_ms,
                    speech_pad_ms=self.speech_pad_ms,
                )
                logger.info("Silero VAD model initialized successfully.")
            except Exception as exc:
                logger.warning("Failed to initialize Silero VAD model: %s. Using energy fallback.", exc)

    @property
    def is_silero_available(self) -> bool:
        return self._silero_model is not None

    def get_speech_timestamps(self, audio: np.ndarray) -> list[SpeechSegment]:
        """Identify intervals of active speech within audio array.

        Args:
            audio: 1D mono float32 numpy array at sample_rate (16000 Hz).

        Returns:
            List of SpeechSegment objects.
        """
        if len(audio) == 0:
            return []

        # Ensure float32 1D array
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        if self._silero_model is not None:
            try:
                raw_segments = get_speech_timestamps(
                    audio,
                    vad_options=self._vad_options,
                    sampling_rate=self.sample_rate,
                )
                segments = []
                for seg in raw_segments:
                    start_s = seg["start"]
                    end_s = seg["end"]
                    segments.append(
                        SpeechSegment(
                            start_sample=start_s,
                            end_sample=end_s,
                            start_sec=start_s / self.sample_rate,
                            end_sec=end_s / self.sample_rate,
                        )
                    )
                if segments:
                    return segments
                if self.mode == "silero":
                    return []
            except Exception as exc:
                logger.debug("Silero VAD failed on frame: %s. Using energy fallback.", exc)

        # Fallback to energy-based silence detection
        return self._energy_fallback_segments(audio)

    def is_speech(self, audio: np.ndarray) -> bool:
        """Return True if human speech is present in audio."""
        segments = self.get_speech_timestamps(audio)
        return len(segments) > 0

    def filter_silence(self, audio: np.ndarray) -> np.ndarray:
        """Return concatenated speech portions of audio, dropping silent periods."""
        segments = self.get_speech_timestamps(audio)
        if not segments:
            return np.zeros(0, dtype=np.float32)

        speech_chunks = []
        for seg in segments:
            speech_chunks.append(audio[seg.start_sample : seg.end_sample])

        if speech_chunks:
            return np.concatenate(speech_chunks)
        return np.zeros(0, dtype=np.float32)

    def _energy_fallback_segments(self, audio: np.ndarray) -> list[SpeechSegment]:
        """Energy-based voice activity detector as fallback."""
        frame_size = int(self.sample_rate * 0.03)  # 30 ms
        hop_size = int(self.sample_rate * 0.01)    # 10 ms
        energy_threshold = 0.02 * (self.threshold / 0.5)

        is_active = []
        for i in range(0, len(audio) - frame_size + 1, hop_size):
            frame = audio[i : i + frame_size]
            rms = calculate_rms(frame)
            is_active.append((i, i + frame_size, rms >= energy_threshold))

        if not is_active:
            return []

        segments: list[SpeechSegment] = []
        in_speech = False
        start_idx = 0

        for start, end, active in is_active:
            if active and not in_speech:
                in_speech = True
                start_idx = start
            elif not active and in_speech:
                in_speech = False
                duration_ms = (end - start_idx) / self.sample_rate * 1000
                if duration_ms >= self.min_speech_duration_ms:
                    segments.append(
                        SpeechSegment(
                            start_sample=start_idx,
                            end_sample=end,
                            start_sec=start_idx / self.sample_rate,
                            end_sec=end / self.sample_rate,
                        )
                    )

        if in_speech:
            duration_ms = (len(audio) - start_idx) / self.sample_rate * 1000
            if duration_ms >= self.min_speech_duration_ms:
                segments.append(
                    SpeechSegment(
                        start_sample=start_idx,
                        end_sample=len(audio),
                        start_sec=start_idx / self.sample_rate,
                        end_sec=len(audio) / self.sample_rate,
                    )
                )

        return segments
