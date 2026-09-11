"""Local LLM meeting synthesis engine with offline extractive fallback."""

import logging
import re

import httpx

from voxlocal.synthesis.prompt_templates import SYSTEM_INSTRUCTION, get_prompt_template
from voxlocal.transcription.whisper_engine import TranscriptSegment

logger = logging.getLogger(__name__)


class Summarizer:
    """Synthesizes structured meeting notes using local Ollama or deterministic fallback."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model_name: str = "llama3.2",
        temperature: float = 0.2,
        timeout_sec: float = 60.0,
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.model_name = model_name
        self.temperature = temperature
        self.timeout_sec = timeout_sec

    def check_ollama_available(self) -> bool:
        """Check if local Ollama daemon is reachable."""
        try:
            with httpx.Client(timeout=2.0) as client:
                res = client.get(f"{self.ollama_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    def format_transcript_text(self, segments: list[TranscriptSegment]) -> str:
        """Render list of TranscriptSegment instances into readable transcript text."""
        lines = []
        for seg in segments:
            lines.append(f"{seg.formatted_timestamp} {seg.speaker}: {seg.text}")
        return "\n".join(lines)

    def summarize(
        self,
        segments: list[TranscriptSegment],
        title: str = "Meeting Notes",
        preset: str = "general",
        local_user: str = "You",
    ) -> str:
        """Generate structured meeting notes.

        Attempts LLM generation via Ollama first; if unavailable, uses offline
        deterministic fallback so meeting notes are never lost.
        """
        transcript_text = self.format_transcript_text(segments)
        if not transcript_text.strip():
            return f"# {title}\n\nNo speech content was detected during this session."

        template = get_prompt_template(preset)
        prompt = template.format(
            title=title,
            transcript=transcript_text,
            local_user=local_user,
        )

        # Attempt Ollama synthesis
        llm_result = self._query_ollama(prompt)
        if llm_result:
            return llm_result.strip()

        # Offline deterministic fallback
        logger.info("Local LLM not accessible. Generating notes using extractive offline fallback.")
        return self._extractive_fallback_summary(segments, title=title, preset=preset)

    def _query_ollama(self, prompt: str) -> str | None:
        """Query local Ollama instance via HTTP POST."""
        url = f"{self.ollama_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": SYSTEM_INSTRUCTION,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    response_text = data.get("response", "")
                    if response_text.strip():
                        return response_text
                else:
                    logger.warning("Ollama returned status code %d: %s", res.status_code, res.text)
        except Exception as exc:
            logger.debug("Failed connecting to Ollama: %s", exc)

        return None

    def _extractive_fallback_summary(
        self,
        segments: list[TranscriptSegment],
        title: str,
        preset: str,
    ) -> str:
        """Deterministic extractive summarization using heuristics and regular expressions."""
        action_patterns = [
            r"\b(i will|i'll|we will|we'll|let's|lets)\b\s+([^.,;!?]+)",
            r"\b(please|make sure to|need to|should)\b\s+([^.,;!?]+)",
            r"\b(assign|action item|task)\b[:\s]+([^.,;!?]+)",
        ]
        decision_patterns = [
            r"\b(agreed|decided|concluded|approved|chosen|we should use|will use)\b\s+([^.,;!?]+)",
        ]

        action_items: list[str] = []
        decisions: list[str] = []
        questions: list[str] = []

        for seg in segments:
            text = seg.text
            # Extract questions
            if "?" in text:
                for q in text.split("?"):
                    q = q.strip()
                    if q and len(q) > 10:
                        questions.append(f"- **{seg.speaker}**: {q}?")

            # Extract actions
            for pat in action_patterns:
                matches = re.finditer(pat, text, re.IGNORECASE)
                for m in matches:
                    task = m.group(0).strip()
                    action_items.append(f"- [ ] @{seg.speaker}: {task.capitalize()}")

            # Extract decisions
            for pat in decision_patterns:
                matches = re.finditer(pat, text, re.IGNORECASE)
                for m in matches:
                    dec = m.group(0).strip()
                    decisions.append(f"- {seg.speaker}: {dec.capitalize()}")

        # Deduplicate while preserving order
        unique_actions = list(dict.fromkeys(action_items))
        unique_decisions = list(dict.fromkeys(decisions))
        unique_questions = list(dict.fromkeys(questions))

        # Build Markdown notes
        md_lines = [
            f"# {title}",
            "",
            "## Executive Summary",
            f"Meeting recorded via VoxLocal with preset `{preset}`. Contains {len(segments)} transcribed dialogue turns.",
            "",
            "## Decisions Made",
        ]

        if unique_decisions:
            md_lines.extend(unique_decisions[:10])
        else:
            md_lines.append("- General discussion held without explicit voting or sign-off phrases.")

        md_lines.extend([
            "",
            "## Action Items",
        ])

        if unique_actions:
            md_lines.extend(unique_actions[:15])
        else:
            md_lines.append("- [ ] @Team: Review meeting transcript and assign follow-up tasks.")

        if unique_questions:
            md_lines.extend([
                "",
                "## Questions Raised",
            ])
            md_lines.extend(unique_questions[:8])

        md_lines.extend([
            "",
            "## Transcript Overview",
            "```text",
            self.format_transcript_text(segments),
            "```",
        ])

        return "\n".join(md_lines)
