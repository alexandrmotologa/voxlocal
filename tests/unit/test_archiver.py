"""Unit tests for audio archiver."""

from pathlib import Path

import numpy as np
from scipy.io import wavfile

from tests.fixtures.synthetic_audio import generate_synthetic_tone
from voxlocal.audio.archiver import AudioArchiver
from voxlocal.audio.mixer import AudioFrame


def test_audio_archiver_saves_wav(tmp_path: Path):
    archiver = AudioArchiver(target_dir=tmp_path, sample_rate=16000)

    tone = generate_synthetic_tone(duration_sec=0.5, sample_rate=16000)
    frame = AudioFrame(data=tone, channel_source="mic", mic_rms=0.5, loopback_rms=0.0, timestamp=0.0)

    archiver.add_frame(frame)
    saved_path = archiver.save("meeting_audio_test")

    assert saved_path is not None
    assert saved_path.exists()
    assert saved_path.suffix == ".wav"

    sr, data = wavfile.read(str(saved_path))
    assert sr == 16000
    assert len(data) == 8000
    assert data.dtype == np.int16
