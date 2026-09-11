"""Unit tests for audio resampling and normalization."""

import numpy as np
import pytest

from voxlocal.audio.resampler import (
    calculate_db,
    calculate_rms,
    normalize_audio,
    resample_audio,
    to_mono,
)


def test_to_mono_1d():
    mono = np.array([0.1, -0.2, 0.3], dtype=np.float32)
    res = to_mono(mono)
    assert res.ndim == 1
    assert np.allclose(res, mono)


def test_to_mono_stereo():
    stereo = np.array([[0.2, 0.4], [-0.1, 0.3]], dtype=np.float32)
    res = to_mono(stereo)
    assert res.ndim == 1
    assert len(res) == 2
    assert pytest.approx(res[0]) == 0.3
    assert pytest.approx(res[1]) == 0.1


def test_resample_audio():
    # 48kHz 1 second signal to 16kHz
    orig_sr = 48000
    target_sr = 16000
    t = np.linspace(0, 1.0, orig_sr, endpoint=False)
    sig = np.sin(2 * np.pi * 400 * t).astype(np.float32)

    resampled = resample_audio(sig, orig_sr=orig_sr, target_sr=target_sr)
    assert len(resampled) == target_sr
    assert resampled.dtype == np.float32


def test_normalize_audio():
    clipped = np.array([1.5, -2.0, 0.5], dtype=np.float32)
    normalized = normalize_audio(clipped)
    assert np.max(normalized) <= 1.0
    assert np.min(normalized) >= -1.0


def test_calculate_rms_and_db():
    silence = np.zeros(100, dtype=np.float32)
    rms = calculate_rms(silence)
    assert rms == 0.0
    assert calculate_db(rms) == -100.0

    loud = np.ones(100, dtype=np.float32)
    assert pytest.approx(calculate_rms(loud), 0.001) == 1.0
    assert pytest.approx(calculate_db(1.0), 0.001) == 0.0
