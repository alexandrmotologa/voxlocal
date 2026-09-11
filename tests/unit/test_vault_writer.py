"""Unit tests for Markdown vault writer and Obsidian frontmatter."""

from pathlib import Path

import yaml

from voxlocal.synthesis.vault_writer import VaultWriter, format_duration, slugify_title
from voxlocal.transcription.diarization import SpeakerStats
from voxlocal.transcription.whisper_engine import TranscriptSegment


def test_slugify_title():
    assert slugify_title("Architecture Review: Q3 Roadmap!") == "architecture-review-q3-roadmap"
    assert slugify_title("1-on-1 Sync with @Alex") == "1-on-1-sync-with-alex"


def test_format_duration():
    assert format_duration(65) == "00:01:05"
    assert format_duration(3665) == "01:01:05"


def test_vault_writer_creates_obsidian_markdown(tmp_path: Path):
    writer = VaultWriter(vault_dir=tmp_path)

    segments = [
        TranscriptSegment(id=1, start=0.0, end=2.0, speaker="You", text="Hello team."),
        TranscriptSegment(id=2, start=2.0, end=5.0, speaker="Remote Speaker 1", text="Hi everyone."),
    ]
    speaker_stats = {
        "You": SpeakerStats(name="You", total_seconds=2.0, total_words=2),
        "Remote Speaker 1": SpeakerStats(name="Remote Speaker 1", total_seconds=3.0, total_words=2),
    }

    summary_md = "## Executive Summary\nTeam alignment call."

    note_file = writer.write_meeting_note(
        title="Weekly Team Sync",
        summary_markdown=summary_md,
        segments=segments,
        speaker_stats=speaker_stats,
        preset="standup",
        duration_sec=300.0,
    )

    assert note_file.exists()
    content = note_file.read_text(encoding="utf-8")

    # Verify YAML frontmatter
    assert content.startswith("---")
    parts = content.split("---", 2)
    assert len(parts) >= 3

    frontmatter = yaml.safe_load(parts[1])
    assert frontmatter["title"] == "Weekly Team Sync"
    assert frontmatter["preset"] == "standup"
    assert "You" in frontmatter["participants"]
    assert "Remote Speaker 1" in frontmatter["participants"]
    assert frontmatter["stats"]["talk_time"]["You"] == "40%"
    assert frontmatter["stats"]["talk_time"]["Remote Speaker 1"] == "60%"

    # Verify Markdown body and verbatim transcript
    assert "## Executive Summary" in content
    assert "## Verbatim Transcript" in content
    assert "**You**: Hello team." in content
    assert "**Remote Speaker 1**: Hi everyone." in content
