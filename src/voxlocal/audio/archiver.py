"""Audio stream archiver saving local meeting recordings."""

from pathlib import Path

import numpy as np
from scipy.io import wavfile

from voxlocal.audio.mixer import AudioFrame
from voxlocal.audio.resampler import normalize_audio


class AudioArchiver:
    """Accumulates and archives audio frames to disk at meeting completion."""

    def __init__(self, target_dir: Path, sample_rate: int = 16000):
        self.target_dir = Path(target_dir)
        self.sample_rate = sample_rate
        self._frames: list[np.ndarray] = []

    def add_frame(self, frame: AudioFrame) -> None:
        """Store mixed audio frame."""
        self._frames.append(frame.data)

    def save(self, filename_stem: str) -> Path | None:
        """Save concatenated audio to 16-bit PCM WAV file.

        Args:
            filename_stem: Safe filename prefix without extension.

        Returns:
            Path to saved WAV file, or None if no audio recorded.
        """
        if not self._frames:
            return None

        self.target_dir.mkdir(parents=True, exist_ok=True)
        full_audio = np.concatenate(self._frames)
        normalized = normalize_audio(full_audio, max_val=0.95)

        # Convert float32 [-1.0, 1.0] to int16 [-32768, 32767]
        pcm16 = (normalized * 32767.0).astype(np.int16)

        out_path = self.target_dir / f"{filename_stem}.wav"
        wavfile.write(str(out_path), self.sample_rate, pcm16)
        return out_path
