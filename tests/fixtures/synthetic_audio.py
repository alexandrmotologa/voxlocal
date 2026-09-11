"""Synthetic audio test generators for unit and integration testing."""

import numpy as np


def generate_silence(duration_sec: float, sample_rate: int = 16000) -> np.ndarray:
    """Generate pure digital silence buffer."""
    samples = int(duration_sec * sample_rate)
    return np.zeros(samples, dtype=np.float32)


def generate_synthetic_tone(
    freq_hz: float = 440.0,
    duration_sec: float = 1.0,
    sample_rate: int = 16000,
    amplitude: float = 0.5,
) -> np.ndarray:
    """Generate a pure sinusoidal tone."""
    samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, samples, endpoint=False, dtype=np.float32)
    return (amplitude * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)


def generate_synthetic_speech_like(
    duration_sec: float = 1.0,
    sample_rate: int = 16000,
    pitch_hz: float = 150.0,
    amplitude: float = 0.6,
) -> np.ndarray:
    """Generate harmonic speech-like signal modulated with vowel-like formants.

    Simulates typical human voice fundamental frequency and formant resonances.
    """
    samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, samples, endpoint=False, dtype=np.float32)

    # Fundamental frequency + vocal tract harmonics (1st, 2nd, 3rd formants)
    f0 = np.sin(2 * np.pi * pitch_hz * t)
    f1 = 0.6 * np.sin(2 * np.pi * (pitch_hz * 3.5) * t)  # ~500 Hz
    f2 = 0.4 * np.sin(2 * np.pi * (pitch_hz * 10.0) * t) # ~1500 Hz
    f3 = 0.2 * np.sin(2 * np.pi * (pitch_hz * 17.0) * t) # ~2500 Hz

    signal = f0 + f1 + f2 + f3

    # Syllabic envelope modulation (approx 4 syllables per second)
    syllable_rate = 4.0
    envelope = 0.5 * (1.0 + np.sin(2 * np.pi * syllable_rate * t - np.pi / 2))
    envelope = np.clip(envelope, 0.05, 1.0)

    modulated = signal * envelope
    # Normalize peak to amplitude
    peak = np.max(np.abs(modulated))
    if peak > 0:
        modulated = (modulated / peak) * amplitude

    return modulated.astype(np.float32)


def generate_conversation_scenario(sample_rate: int = 16000):
    """Generate a 4-second conversation:

    0.0s - 1.5s: Local Mic speaks ("You")
    1.5s - 2.5s: Complete silence (thinking pause)
    2.5s - 4.0s: System Loopback speaks ("Remote Speaker")
    """
    speech_you = generate_synthetic_speech_like(duration_sec=1.5, sample_rate=sample_rate, pitch_hz=130.0)
    silence_you = generate_silence(duration_sec=2.5, sample_rate=sample_rate)
    mic_track = np.concatenate([speech_you, silence_you])

    silence_remote = generate_silence(duration_sec=2.5, sample_rate=sample_rate)
    speech_remote = generate_synthetic_speech_like(duration_sec=1.5, sample_rate=sample_rate, pitch_hz=210.0)
    loopback_track = np.concatenate([silence_remote, speech_remote])

    return mic_track, loopback_track
