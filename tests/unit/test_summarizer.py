"""Unit tests for meeting note summarization and offline fallback."""


from voxlocal.synthesis.summarizer import Summarizer
from voxlocal.transcription.whisper_engine import TranscriptSegment


def test_extractive_fallback_summary_action_items():
    summarizer = Summarizer()

    segments = [
        TranscriptSegment(id=1, start=0.0, end=2.0, speaker="You", text="We need to migrate the database to PostgreSQL."),
        TranscriptSegment(id=2, start=2.0, end=4.0, speaker="Remote Speaker 1", text="Agreed, we will use Flyway for database schema migrations."),
        TranscriptSegment(id=3, start=4.0, end=6.0, speaker="You", text="I will write the initial migration script by tomorrow."),
        TranscriptSegment(id=4, start=6.0, end=8.0, speaker="Remote Speaker 1", text="Can we deploy it on Tuesday?"),
    ]

    summary = summarizer.summarize(segments, title="Database Migration Sync", preset="architecture_review")

    assert "# Database Migration Sync" in summary
    assert "## Decisions Made" in summary
    assert "## Action Items" in summary
    # Action item regex should have detected "I will write"
    assert "@You: I will write the initial migration script by tomorrow" in summary or "@You:" in summary
    assert "## Questions Raised" in summary
    assert "Can we deploy it on Tuesday?" in summary


def test_summarizer_empty_transcript():
    summarizer = Summarizer()
    summary = summarizer.summarize([], title="Empty Meeting")
    assert "No speech content was detected" in summary
