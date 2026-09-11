"""Unit tests for streaming audio chunker."""


from tests.fixtures.synthetic_audio import generate_silence, generate_synthetic_speech_like
from voxlocal.audio.mixer import AudioFrame
from voxlocal.audio.vad import VoiceActivityDetector
from voxlocal.transcription.chunker import StreamingAudioChunker


def test_chunker_accumulation():
    # Force energy mode on VAD for synthetic tests
    vad = VoiceActivityDetector(threshold=0.3, mode="energy")
    chunker = StreamingAudioChunker(
        sample_rate=16000,
        chunk_duration_sec=1.0,  # 1 second chunks for test speed
        overlap_sec=0.2,
        vad_detector=vad,
    )

    # Feed 16000 samples of speech-like audio in 512-sample frames
    speech = generate_synthetic_speech_like(duration_sec=1.5, sample_rate=16000)
    frames_count = len(speech) // 512

    extracted_chunks = []
    for i in range(frames_count):
        sub = speech[i * 512 : (i + 1) * 512]
        frame = AudioFrame(
            data=sub,
            channel_source="mic",
            mic_rms=0.2,
            loopback_rms=0.0,
            timestamp=0.0,
        )
        chunker.add_frame(frame)
        chunk = chunker.extract_chunk()
        if chunk:
            extracted_chunks.append(chunk)

    assert len(extracted_chunks) >= 1
    first = extracted_chunks[0]
    assert first.primary_channel == "mic"
    assert len(first.data) == 16000  # 1.0s * 16000


def test_chunker_drops_complete_silence():
    vad = VoiceActivityDetector(threshold=0.5, mode="energy")
    chunker = StreamingAudioChunker(
        sample_rate=16000,
        chunk_duration_sec=1.0,
        overlap_sec=0.2,
        vad_detector=vad,
    )

    silence = generate_silence(duration_sec=2.0, sample_rate=16000)
    frames_count = len(silence) // 512

    for i in range(frames_count):
        sub = silence[i * 512 : (i + 1) * 512]
        frame = AudioFrame(
            data=sub,
            channel_source="loopback",
            mic_rms=0.0,
            loopback_rms=0.0,
            timestamp=0.0,
        )
        chunker.add_frame(frame)
        chunk = chunker.extract_chunk()
        # Silent chunks should be dropped by VAD
        assert chunk is None
