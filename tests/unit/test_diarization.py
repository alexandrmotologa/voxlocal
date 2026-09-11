"""Unit tests for speaker diarization."""


from tests.fixtures.synthetic_audio import generate_synthetic_speech_like
from voxlocal.transcription.chunker import AudioChunk
from voxlocal.transcription.diarization import SpeakerDiarizer


def test_diarizer_attributes_mic_to_local_user():
    diarizer = SpeakerDiarizer(local_user_name="You")

    audio = generate_synthetic_speech_like(duration_sec=1.0, sample_rate=16000)
    chunk = AudioChunk(
        data=audio,
        start_time=0.0,
        end_time=1.0,
        primary_channel="mic",
        speech_ratio=0.9,
    )

    speaker = diarizer.attribute_speaker(chunk)
    assert speaker == "You"
    assert diarizer.speaker_stats["You"].total_seconds == 1.0


def test_diarizer_clusters_remote_speakers():
    diarizer = SpeakerDiarizer(cluster_threshold=0.8)

    # Remote voice 1: deep voice (pitch 120Hz)
    voice_low = generate_synthetic_speech_like(duration_sec=1.0, pitch_hz=120.0)
    chunk_1 = AudioChunk(
        data=voice_low,
        start_time=0.0,
        end_time=1.0,
        primary_channel="loopback",
        speech_ratio=1.0,
    )
    speaker_1 = diarizer.attribute_speaker(chunk_1)
    assert speaker_1 == "Remote Speaker 1"

    # Same remote voice 1 again -> should cluster to Remote Speaker 1
    chunk_1_repeat = AudioChunk(
        data=voice_low,
        start_time=1.0,
        end_time=2.0,
        primary_channel="loopback",
        speech_ratio=1.0,
    )
    speaker_1_again = diarizer.attribute_speaker(chunk_1_repeat)
    assert speaker_1_again == "Remote Speaker 1"

    # Remote voice 2: high pitch voice (pitch 400Hz)
    voice_high = generate_synthetic_speech_like(duration_sec=1.0, pitch_hz=400.0)
    chunk_2 = AudioChunk(
        data=voice_high,
        start_time=2.0,
        end_time=3.0,
        primary_channel="loopback",
        speech_ratio=1.0,
    )
    speaker_2 = diarizer.attribute_speaker(chunk_2)
    assert speaker_2 == "Remote Speaker 2"


def test_diarizer_talk_time_summary():
    diarizer = SpeakerDiarizer(local_user_name="You")

    audio = generate_synthetic_speech_like(duration_sec=1.0)
    chunk_you = AudioChunk(data=audio, start_time=0.0, end_time=1.0, primary_channel="mic", speech_ratio=1.0)
    chunk_remote = AudioChunk(data=audio, start_time=1.0, end_time=3.0, primary_channel="loopback", speech_ratio=1.0)

    diarizer.attribute_speaker(chunk_you)
    diarizer.attribute_speaker(chunk_remote)

    summary = diarizer.get_talk_time_summary()
    assert summary["You"] == "33%"
    assert summary["Remote Speaker 1"] == "67%"
