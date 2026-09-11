"""Streaming audio chunker with sliding ring buffer and speech boundary alignment."""

from dataclasses import dataclass
from typing import Literal

import numpy as np

from voxlocal.audio.mixer import AudioFrame
from voxlocal.audio.vad import VoiceActivityDetector


@dataclass
class AudioChunk:
    """A sliced window of audio ready for transcription."""

    data: np.ndarray
    start_time: float
    end_time: float
    primary_channel: Literal["mic", "loopback", "mixed"]
    speech_ratio: float


class StreamingAudioChunker:
    """Accumulates incoming AudioFrames and yields sliding audio chunks."""

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_duration_sec: float = 3.0,
        overlap_sec: float = 0.5,
        vad_detector: VoiceActivityDetector | None = None,
    ):
        self.sample_rate = sample_rate
        self.chunk_duration_sec = chunk_duration_sec
        self.overlap_sec = overlap_sec
        self.chunk_samples = int(chunk_duration_sec * sample_rate)
        self.overlap_samples = int(overlap_sec * sample_rate)
        self.step_samples = self.chunk_samples - self.overlap_samples
        self.vad = vad_detector or VoiceActivityDetector(sample_rate=sample_rate)

        self._audio_buffer = np.zeros(0, dtype=np.float32)
        self._channel_tags: list[str] = []
        self._samples_processed = 0

    @property
    def total_elapsed_sec(self) -> float:
        return self._samples_processed / self.sample_rate

    def add_frame(self, frame: AudioFrame) -> None:
        """Append incoming audio frame to internal ring buffer."""
        self._audio_buffer = np.concatenate((self._audio_buffer, frame.data))
        # Tag channel for each sample in frame
        tag = frame.channel_source
        self._channel_tags.extend([tag] * len(frame.data))

    def can_extract_chunk(self) -> bool:
        """Check if buffer has enough samples for a chunk."""
        return len(self._audio_buffer) >= self.chunk_samples

    def extract_chunk(self) -> AudioChunk | None:
        """Extract next sliding chunk if enough audio has accumulated.

        Advances buffer by step_samples, retaining overlap_samples.
        """
        if not self.can_extract_chunk():
            return None

        chunk_data = self._audio_buffer[: self.chunk_samples]
        chunk_tags = self._channel_tags[: self.chunk_samples]

        start_time = self._samples_processed / self.sample_rate
        end_time = start_time + (self.chunk_samples / self.sample_rate)

        # Advance buffer by step_samples
        self._audio_buffer = self._audio_buffer[self.step_samples :]
        self._channel_tags = self._channel_tags[self.step_samples :]
        self._samples_processed += self.step_samples

        # Determine dominant channel
        mic_count = chunk_tags.count("mic")
        loopback_count = chunk_tags.count("loopback")
        total = len(chunk_tags)

        if mic_count / total > 0.6:
            primary_channel = "mic"
        elif loopback_count / total > 0.6:
            primary_channel = "loopback"
        else:
            primary_channel = "mixed"

        # Check VAD speech presence
        is_speech = self.vad.is_speech(chunk_data)
        if not is_speech:
            # Entirely silent or noise: return None to skip transcription
            return None

        segments = self.vad.get_speech_timestamps(chunk_data)
        speech_samples = sum(s.end_sample - s.start_sample for s in segments)
        speech_ratio = speech_samples / len(chunk_data) if len(chunk_data) > 0 else 0.0

        return AudioChunk(
            data=chunk_data,
            start_time=start_time,
            end_time=end_time,
            primary_channel=primary_channel,
            speech_ratio=speech_ratio,
        )

    def flush(self) -> AudioChunk | None:
        """Flush remaining buffer at session end."""
        min_samples = int(0.5 * self.sample_rate)  # At least 0.5s of audio
        if len(self._audio_buffer) < min_samples:
            self._audio_buffer = np.zeros(0, dtype=np.float32)
            self._channel_tags.clear()
            return None

        chunk_data = self._audio_buffer
        start_time = self._samples_processed / self.sample_rate
        end_time = start_time + (len(chunk_data) / self.sample_rate)

        mic_count = self._channel_tags.count("mic")
        loopback_count = self._channel_tags.count("loopback")
        total = len(self._channel_tags)

        primary_channel = "mic" if mic_count >= loopback_count else "loopback"
        if total > 0 and (mic_count / total > 0.4 and loopback_count / total > 0.4):
            primary_channel = "mixed"

        self._audio_buffer = np.zeros(0, dtype=np.float32)
        self._channel_tags.clear()

        if not self.vad.is_speech(chunk_data):
            return None

        return AudioChunk(
            data=chunk_data,
            start_time=start_time,
            end_time=end_time,
            primary_channel=primary_channel,
            speech_ratio=1.0,
        )
