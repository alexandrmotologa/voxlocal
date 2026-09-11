"""Unit tests for Voice Activity Detection."""

import numpy as np

from tests.fixtures.synthetic_audio import generate_silence, generate_synthetic_speech_like
from voxlocal.audio.vad import VoiceActivityDetector


def test_vad_silence_detection():
    vad = VoiceActivityDetector(threshold=0.5)
    silence = generate_silence(duration_sec=1.0, sample_rate=16000)

    segments = vad.get_speech_timestamps(silence)
    assert len(segments) == 0
    assert not vad.is_speech(silence)

    filtered = vad.filter_silence(silence)
    assert len(filtered) == 0


def test_vad_speech_detection():
    vad = VoiceActivityDetector(threshold=0.4, min_speech_duration_ms=100)
    speech = generate_synthetic_speech_like(duration_sec=1.5, sample_rate=16000, amplitude=0.8)

    # Note: If Silero model is active or energy fallback is active, speech should be detected
    is_active = vad.is_speech(speech)
    assert is_active is True


def test_vad_filter_silence_cuts_dead_air():
    vad = VoiceActivityDetector(threshold=0.4, min_speech_duration_ms=100)
    speech = generate_synthetic_speech_like(duration_sec=1.0, sample_rate=16000, amplitude=0.8)
    silence = generate_silence(duration_sec=2.0, sample_rate=16000)

    combined = np.concatenate([silence, speech, silence])
    filtered = vad.filter_silence(combined)

    # Filtered audio should be substantially shorter than original 4 seconds
    assert len(filtered) < len(combined)
