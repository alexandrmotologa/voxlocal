"""End-to-end integration test of the full VoxLocal audio pipeline."""

from pathlib import Path

import numpy as np

from tests.fixtures.synthetic_audio import generate_conversation_scenario
from voxlocal.audio.mixer import DualChannelAudioMixer
from voxlocal.audio.vad import VoiceActivityDetector
from voxlocal.synthesis.summarizer import Summarizer
from voxlocal.synthesis.vault_writer import VaultWriter
from voxlocal.transcription.chunker import StreamingAudioChunker
from voxlocal.transcription.diarization import SpeakerDiarizer
from voxlocal.transcription.whisper_engine import TranscriptSegment, TranscriptWord


def test_full_pipeline_e2e(tmp_path: Path):
    """Verify complete flow: Synthetic Audio -> Mixer -> Chunker -> Diarizer -> Whisper -> Summarizer -> VaultWriter."""
    sample_rate = 16000
    mic_track, loopback_track = generate_conversation_scenario(sample_rate=sample_rate)

    # 1. Initialize mixer
    mixer = DualChannelAudioMixer(target_sr=sample_rate, frame_samples=512)

    # Feed conversation scenario in 512-sample slices
    num_frames = min(len(mic_track), len(loopback_track)) // 512
    for i in range(num_frames):
        m_slice = mic_track[i * 512 : (i + 1) * 512]
        l_slice = loopback_track[i * 512 : (i + 1) * 512]
        mixer.on_mic_data(m_slice, rms=float(np.sqrt(np.mean(np.square(m_slice)))))
        mixer.on_loopback_data(l_slice, rms=float(np.sqrt(np.mean(np.square(l_slice)))))

    # 2. Chunker with energy-aware VAD
    vad = VoiceActivityDetector(threshold=0.3, sample_rate=sample_rate, mode="energy")
    chunker = StreamingAudioChunker(
        sample_rate=sample_rate,
        chunk_duration_sec=1.5,
        overlap_sec=0.2,
        vad_detector=vad,
    )

    while True:
        frame = mixer.pull_frame(timeout=0.01)
        if frame is None:
            break
        chunker.add_frame(frame)

    # 3. Extract chunks and attribute speakers
    diarizer = SpeakerDiarizer(local_user_name="You")
    chunks = []
    while True:
        chunk = chunker.extract_chunk()
        if chunk is None:
            break
        chunks.append(chunk)

    final_chunk = chunker.flush()
    if final_chunk:
        chunks.append(final_chunk)

    assert len(chunks) >= 1, "Should have extracted active speech chunks"

    # 4. Whisper transcription simulation
    segments = []
    for idx, c in enumerate(chunks):
        speaker = diarizer.attribute_speaker(c, sample_rate=sample_rate)
        text = "I will deploy the new API service." if speaker == "You" else "We agreed on the database schema."
        seg = TranscriptSegment(
            id=idx + 1,
            start=c.start_time,
            end=c.end_time,
            text=text,
            speaker=speaker,
            channel=c.primary_channel,
            words=[TranscriptWord(word=w, start=c.start_time, end=c.end_time, probability=0.95) for w in text.split()],
        )
        segments.append(seg)
        diarizer.record_words(speaker, len(text.split()))

    assert len(segments) >= 1

    # 5. Summarizer
    summarizer = Summarizer()
    summary_md = summarizer.summarize(
        segments=segments,
        title="Sprint Sync Test",
        preset="standup",
        local_user="You",
    )

    assert "## Decisions Made" in summary_md or "## Action Items" in summary_md

    # 6. Vault Writer
    writer = VaultWriter(vault_dir=tmp_path)
    note_path = writer.write_meeting_note(
        title="Sprint Sync Test",
        summary_markdown=summary_md,
        segments=segments,
        speaker_stats=diarizer.speaker_stats,
        preset="standup",
        duration_sec=4.0,
    )

    assert note_path.exists()
    content = note_path.read_text(encoding="utf-8")
    assert "title: Sprint Sync Test" in content
    assert "preset: standup" in content
    assert "## Verbatim Transcript" in content
