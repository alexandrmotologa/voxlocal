"""Markdown vault writer supporting Obsidian frontmatter and structured notes."""

import re
from datetime import datetime
from pathlib import Path

import yaml

from voxlocal.transcription.diarization import SpeakerStats
from voxlocal.transcription.whisper_engine import TranscriptSegment


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
        return target_file
