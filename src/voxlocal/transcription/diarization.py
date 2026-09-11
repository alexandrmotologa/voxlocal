"""Hardware-informed speaker diarization and talk-time attribution."""

from dataclasses import dataclass

import numpy as np

from voxlocal.transcription.chunker import AudioChunk


@dataclass
class SpeakerStats:
    """Talk-time and segment statistics for an individual speaker."""

    name: str
    total_seconds: float = 0.0
    segment_count: int = 0
    total_words: int = 0


@dataclass
class SpeakerProfile:
    """Acoustic signature for clustering remote meeting participants."""

    speaker_id: str
    centroid_mean: float
    zcr_mean: float
    sample_count: int = 1

    def distance_to(self, centroid: float, zcr: float) -> float:
        """Compute normalized euclidean distance to feature tuple."""
        # Spectral centroid typically ranges 500-3000 Hz, ZCR 0.01-0.2
        norm_c = (self.centroid_mean - centroid) / 1000.0
        norm_z = (self.zcr_mean - zcr) / 0.1
        return float(np.sqrt(norm_c**2 + norm_z**2))

    def update(self, centroid: float, zcr: float) -> None:
        """Moving average update of speaker profile."""
        alpha = 1.0 / (self.sample_count + 1)
        self.centroid_mean = (1 - alpha) * self.centroid_mean + alpha * centroid
        self.zcr_mean = (1 - alpha) * self.zcr_mean + alpha * zcr
        self.sample_count += 1


class SpeakerDiarizer:
    """Attributes audio segments to speakers using hardware channels and acoustic clustering."""

    def __init__(
        self,
        local_user_name: str = "You",
        cluster_threshold: float = 1.2,
    ):
        self.local_user_name = local_user_name
        self.cluster_threshold = cluster_threshold

        self._remote_profiles: list[SpeakerProfile] = []
        self._stats: dict[str, SpeakerStats] = {
            self.local_user_name: SpeakerStats(name=self.local_user_name)
        }

    @property
    def speaker_stats(self) -> dict[str, SpeakerStats]:
        return self._stats

    def compute_acoustic_features(self, audio: np.ndarray, sample_rate: int = 16000) -> tuple[float, float]:
        """Extract spectral centroid and zero crossing rate from audio buffer."""
        if len(audio) < 256:
            return 1000.0, 0.05

        # Zero crossing rate
        signs = np.sign(audio)
        signs[signs == 0] = 1
        zcr = float(np.mean(np.abs(signs[1:] - signs[:-1])) / 2.0)

        # Spectral Centroid via FFT
        fft = np.abs(np.fft.rfft(audio))
        freqs = np.fft.rfftfreq(len(audio), d=1.0 / sample_rate)
        sum_fft = np.sum(fft)
        if sum_fft > 1e-7:
            centroid = float(np.sum(freqs * fft) / sum_fft)
        else:
            centroid = 1000.0

        return centroid, zcr

    def attribute_speaker(self, chunk: AudioChunk, sample_rate: int = 16000) -> str:
        """Determine speaker identity for the audio chunk.

        - "mic" -> Local user ("You")
        - "loopback" -> Remote participant (clustered by acoustic profile)
        - "mixed" -> Cross-talk / Shared discussion
        """
        if chunk.primary_channel == "mic":
            speaker = self.local_user_name
        elif chunk.primary_channel == "mixed":
            speaker = "Discussion / Cross-talk"
        else:
            # Loopback: distinguish between remote participants
            centroid, zcr = self.compute_acoustic_features(chunk.data, sample_rate=sample_rate)

            best_match: SpeakerProfile | None = None
            min_dist = float("inf")

            for prof in self._remote_profiles:
                dist = prof.distance_to(centroid, zcr)
                if dist < min_dist:
                    min_dist = dist
                    best_match = prof

            if best_match is not None and min_dist <= self.cluster_threshold:
                best_match.update(centroid, zcr)
                speaker = best_match.speaker_id
            else:
                # Create a new remote speaker profile
                speaker_num = len(self._remote_profiles) + 1
                speaker = f"Remote Speaker {speaker_num}"
                new_prof = SpeakerProfile(
                    speaker_id=speaker,
                    centroid_mean=centroid,
                    zcr_mean=zcr,
                )
                self._remote_profiles.append(new_prof)

        # Update statistics
        duration = max(0.0, chunk.end_time - chunk.start_time)
        if speaker not in self._stats:
            self._stats[speaker] = SpeakerStats(name=speaker)

        self._stats[speaker].total_seconds += duration
        self._stats[speaker].segment_count += 1

        return speaker

    def record_words(self, speaker: str, word_count: int) -> None:
        """Record number of words spoken by speaker."""
        if speaker in self._stats:
            self._stats[speaker].total_words += word_count

    def get_talk_time_summary(self) -> dict[str, str]:
        """Calculate percentage talk-time ratios for each speaker."""
        total_time = sum(s.total_seconds for s in self._stats.values())
        if total_time <= 0.001:
            return {s: "0%" for s in self._stats}

        summary = {}
        for name, stat in self._stats.items():
            pct = round((stat.total_seconds / total_time) * 100)
            summary[name] = f"{pct}%"
        return summary
