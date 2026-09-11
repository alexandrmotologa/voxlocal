"""Markdown vault writer supporting Obsidian frontmatter and structured notes."""

import logging
import os
import re
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path

import yaml

from voxlocal.transcription.diarization import SpeakerStats
from voxlocal.transcription.whisper_engine import TranscriptSegment

logger = logging.getLogger(__name__)


def slugify_title(title: str) -> str:
    """Create filesystem-safe slug from title."""
    cleaned = re.sub(r"[^\w\s-]", "", title.lower())
    return re.sub(r"[-\s]+", "-", cleaned).strip("-")


def format_duration(seconds: float) -> str:
    """Format duration in seconds into HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class VaultWriter:
    """Writes synthesized meeting notes to Markdown files in local vaults."""

    def __init__(self, vault_dir: Path):
        self.vault_dir = Path(vault_dir)
        self.vault_dir.mkdir(parents=True, exist_ok=True)

    def write_meeting_note(
        self,
        title: str,
        summary_markdown: str,
        segments: list[TranscriptSegment],
        speaker_stats: dict[str, SpeakerStats],
        preset: str = "general",
        start_time: datetime | None = None,
        duration_sec: float = 0.0,
        extra_tags: list[str] | None = None,
        audio_path: Path | None = None,
        open_in_obsidian: bool = False,
        git_commit: bool = False,
    ) -> Path:
        """Construct frontmatter, combine with summary markdown, and write to vault."""
        now = start_time or datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        participants = list(speaker_stats.keys())
        total_words = sum(s.total_words for s in speaker_stats.values())
        if total_words == 0:
            total_words = sum(len(seg.text.split()) for seg in segments)

        # Compute talk time ratios
        total_time = sum(s.total_seconds for s in speaker_stats.values())
        talk_time_dict = {}
        for name, stat in speaker_stats.items():
            pct = round(stat.total_seconds / total_time * 100) if total_time > 0 else 0
            talk_time_dict[name] = f"{pct}%"

        tags = ["meeting", "voxlocal", preset]
        if extra_tags:
            tags.extend(extra_tags)
        tags = list(dict.fromkeys(tags))

        frontmatter_data = {
            "title": title,
            "date": date_str,
            "time": time_str,
            "duration": format_duration(duration_sec),
            "preset": preset,
            "participants": participants,
            "stats": {
                "total_words": total_words,
                "total_segments": len(segments),
                "talk_time": talk_time_dict,
            },
            "tags": tags,
        }

        if audio_path:
            try:
                rel_audio = os.path.relpath(audio_path, self.vault_dir)
            except ValueError:
                rel_audio = str(audio_path)
            frontmatter_data["audio_file"] = rel_audio

        # Dump YAML frontmatter
        yaml_str = yaml.dump(frontmatter_data, sort_keys=False, default_flow_style=False)
        frontmatter_block = f"---\n{yaml_str}---\n\n"

        # Verbatim transcript appendix
        transcript_lines = []
        for seg in segments:
            transcript_lines.append(f"{seg.formatted_timestamp} **{seg.speaker}**: {seg.text}")
        verbatim_block = "\n\n## Verbatim Transcript\n" + "\n".join(transcript_lines)

        full_content = frontmatter_block + summary_markdown + verbatim_block

        # Determine file path
        slug = slugify_title(title)
        filename = f"{date_str}_{slug}.md"
        target_file = self.vault_dir / filename

        # Avoid collision if multiple meetings on same day have same name
        counter = 1
        while target_file.exists():
            target_file = self.vault_dir / f"{date_str}_{slug}_{counter}.md"
            counter += 1

        target_file.write_text(full_content, encoding="utf-8")

        # Auto-index meeting into SQLite FTS5 database
        try:
            from voxlocal.knowledge.database import KnowledgeDB
            db = KnowledgeDB()
            db.index_meeting(
                title=title,
                date=date_str,
                duration=format_duration(duration_sec),
                preset=preset,
                participants=participants,
                vault_file=target_file,
                summary=summary_markdown,
                segments=segments,
            )
            logger.info("Indexed meeting '%s' into local knowledge base.", title)
        except Exception as exc:
            logger.debug("Failed auto-indexing meeting into knowledge base: %s", exc)

        # Auto-open in Obsidian or system editor if requested
        if open_in_obsidian:
            self._open_in_obsidian(target_file)

        # Git auto-commit if requested
        if git_commit:
            self._git_commit_file(target_file, title)

        return target_file

    def _open_in_obsidian(self, file_path: Path) -> None:
        """Trigger Obsidian protocol or OS file open."""
        try:
            vault_name = self.vault_dir.name
            obsidian_uri = f"obsidian://open?vault={vault_name}&file={file_path.stem}"
            webbrowser.open(obsidian_uri)
            logger.info("Triggered Obsidian open URI: %s", obsidian_uri)
        except Exception as exc:
            logger.debug("Failed opening via obsidian URI: %s", exc)

    def _git_commit_file(self, file_path: Path, title: str) -> None:
        """Commit new note to Git repository inside vault_dir."""
        try:
            subprocess.run(["git", "add", str(file_path)], cwd=str(self.vault_dir), check=True, capture_output=True)
            msg = f"docs(meeting): record {title}"
            subprocess.run(["git", "commit", "-m", msg], cwd=str(self.vault_dir), check=True, capture_output=True)
            logger.info("Committed %s to Git vault.", file_path.name)
        except Exception as exc:
            logger.debug("Git commit in vault failed: %s", exc)
