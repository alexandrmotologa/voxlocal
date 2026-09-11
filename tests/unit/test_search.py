"""Unit tests for SQLite FTS5 meeting indexing and search."""

from pathlib import Path

from voxlocal.knowledge.database import KnowledgeDB
from voxlocal.knowledge.search import ask_meetings
from voxlocal.transcription.whisper_engine import TranscriptSegment


def test_index_and_fts_search(tmp_path: Path):
    db_file = tmp_path / "test_knowledge.db"
    db = KnowledgeDB(db_path=db_file)

    segments = [
        TranscriptSegment(id=1, start=0.0, end=3.0, speaker="You", text="We decided to use Flyway for database schema migrations."),
        TranscriptSegment(id=2, start=3.0, end=6.0, speaker="Remote Speaker 1", text="Yes, Flyway works well with PostgreSQL."),
        TranscriptSegment(id=3, start=6.0, end=9.0, speaker="Remote Speaker 2", text="What about MongoDB?"),
    ]

    meeting_id = db.index_meeting(
        title="Architecture Discussion",
        date="2026-09-12",
        duration="00:15:00",
        preset="architecture_review",
        participants=["You", "Remote Speaker 1", "Remote Speaker 2"],
        vault_file=tmp_path / "note.md",
        summary="Database migration plan",
        segments=segments,
    )

    assert meeting_id == 1

    # FTS query for Flyway
    results = db.search("Flyway")
    assert len(results) == 2
    assert results[0].title == "Architecture Discussion"
    assert "Flyway" in results[0].text

    # Search for non-existent word
    no_results = db.search("Kubernetes")
    assert len(no_results) == 0


def test_ask_meetings_offline_fallback(tmp_path: Path):
    db_file = tmp_path / "test_knowledge.db"
    db = KnowledgeDB(db_path=db_file)

    segments = [
        TranscriptSegment(id=1, start=0.0, end=3.0, speaker="You", text="The deployment target is AWS us-east-1."),
    ]
    db.index_meeting(
        title="Cloud Deployment",
        date="2026-09-12",
        duration="00:05:00",
        preset="general",
        participants=["You"],
        vault_file=tmp_path / "deploy.md",
        summary="Cloud setup",
        segments=segments,
    )

    # Ask without active Ollama server
    answer = ask_meetings("deployment", db=db, ollama_url="http://localhost:99999")
    assert "Cloud Deployment" in answer
    assert "AWS us-east-1" in answer
