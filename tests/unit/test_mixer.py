"""Unit tests for dual-channel audio mixer."""


from tests.fixtures.synthetic_audio import generate_silence, generate_synthetic_speech_like
from voxlocal.audio.mixer import DualChannelAudioMixer


def test_mixer_channel_separation():
    mixer = DualChannelAudioMixer(target_sr=16000, frame_samples=512)

    # 1024 samples of speech on mic, silence on loopback
    mic_audio = generate_synthetic_speech_like(duration_sec=0.1, sample_rate=16000, amplitude=0.8)
    loopback_silence = generate_silence(duration_sec=0.1, sample_rate=16000)

    mixer.on_mic_data(mic_audio, rms=0.4)
    mixer.on_loopback_data(loopback_silence, rms=0.0)

    frame = mixer.pull_frame(timeout=0.1)
    assert frame is not None
    assert frame.channel_source == "mic"
    assert frame.mic_rms > 0.02
    assert frame.loopback_rms < 0.01


def test_mixer_loopback_dominance():
    mixer = DualChannelAudioMixer(target_sr=16000, frame_samples=512)

    mic_silence = generate_silence(duration_sec=0.1, sample_rate=16000)
    loopback_audio = generate_synthetic_speech_like(duration_sec=0.1, sample_rate=16000, amplitude=0.7)

    mixer.on_mic_data(mic_silence, rms=0.0)
    mixer.on_loopback_data(loopback_audio, rms=0.35)

    frame = mixer.pull_frame(timeout=0.1)
    assert frame is not None
    assert frame.channel_source == "loopback"
    assert frame.loopback_rms > 0.02
    assert frame.mic_rms < 0.01


def test_mixer_mixed_speech():
    mixer = DualChannelAudioMixer(target_sr=16000, frame_samples=512)

    speech_a = generate_synthetic_speech_like(duration_sec=0.1, sample_rate=16000, amplitude=0.6)
    speech_b = generate_synthetic_speech_like(duration_sec=0.1, sample_rate=16000, amplitude=0.6)

    mixer.on_mic_data(speech_a, rms=0.3)
    mixer.on_loopback_data(speech_b, rms=0.3)

    frame = mixer.pull_frame(timeout=0.1)
    assert frame is not None
    assert frame.channel_source == "mixed"
