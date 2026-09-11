"""Audio resampling, downmixing, and amplitude normalization utilities."""

import math

import numpy as np
from scipy import signal


def to_mono(audio: np.ndarray) -> np.ndarray:
    """Downmix multi-channel audio to single-channel mono float32.

    Args:
        audio: 1D or 2D numpy array of audio samples.

    Returns:
        1D numpy array of mono audio float32.
    """
    if audio.ndim == 1:
        return audio.astype(np.float32)
    elif audio.ndim == 2:
        # Average across channels (shape: [samples, channels])
        return np.mean(audio, axis=1, dtype=np.float32)
    else:
        raise ValueError(f"Unsupported audio array dimension: {audio.ndim}")


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int = 16000) -> np.ndarray:
    """Resample 1D mono audio from orig_sr to target_sr using polyphase filtering.

    Args:
        audio: 1D numpy array of mono audio.
        orig_sr: Original sample rate in Hz.
        target_sr: Target sample rate in Hz (default 16000).

    Returns:
        1D numpy array resampled to target_sr.
    """
    if orig_sr == target_sr:
        return audio.astype(np.float32)

    gcd = math.gcd(orig_sr, target_sr)
    up = target_sr // gcd
    down = orig_sr // gcd

    # Use resample_poly for fast, band-limited FIR resampling
    resampled = signal.resample_poly(audio, up, down).astype(np.float32)
    return resampled


def normalize_audio(audio: np.ndarray, max_val: float = 0.95) -> np.ndarray:
    """Normalize audio amplitude to prevent digital clipping and ensure stable inference.

    Args:
        audio: 1D numpy array of audio samples.
        max_val: Target peak amplitude scale.

    Returns:
        Amplitude-normalized float32 audio array.
    """
    peak = np.max(np.abs(audio))
    if peak > 1.0:
        return np.clip(audio, -1.0, 1.0)
    elif peak > 0.001 and peak < 0.3:
        # Boost soft audio slightly without clipping
        gain = min(max_val / peak, 3.0)
        return (audio * gain).astype(np.float32)
    return audio.astype(np.float32)


def calculate_rms(audio: np.ndarray) -> float:
    """Calculate Root Mean Square (RMS) energy of an audio frame."""
    if len(audio) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio))))


def calculate_db(rms: float, ref: float = 1.0) -> float:
    """Convert RMS amplitude to decibels relative to full scale (dBFS)."""
    if rms <= 1e-7:
        return -100.0
    return float(20.0 * np.log10(rms / ref))
