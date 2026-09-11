"""Rich TUI widgets for live terminal meeting recording HUD."""


from typing import ClassVar

from rich.console import Console, ConsoleOptions, RenderResult
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from voxlocal.transcription.whisper_engine import TranscriptSegment


class AudioVuMeter:
    """Renders a graphical VU level bar with decibel indication."""

    def __init__(self, label: str, rms: float = 0.0, bar_width: int = 24):
        self.label = label
        self.rms = max(0.0, min(rms, 1.0))
        self.bar_width = bar_width

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        filled = int(self.rms * self.bar_width * 3.0)  # scale up for visual response
        filled = min(filled, self.bar_width)

        bar_text = Text()
        bar_text.append(f"{self.label:<10} [")
        for i in range(self.bar_width):
            if i < filled:
                if i < self.bar_width * 0.6:
                    bar_text.append("■", style="bold green")
                elif i < self.bar_width * 0.85:
                    bar_text.append("■", style="bold yellow")
                else:
                    bar_text.append("■", style="bold red")
            else:
                bar_text.append("·", style="dim white")
        bar_text.append("] ")

        bar_text.append(f"{self.rms:.3f}", style="cyan")
        yield bar_text


class TranscriptFeed:
    """Renders real-time scrolling transcript segments."""

    SPEAKER_COLORS: ClassVar[dict[str, str]] = {
        "You": "bold cyan",
        "Remote Speaker 1": "bold green",
        "Remote Speaker 2": "bold yellow",
        "Remote Speaker 3": "bold magenta",
        "Discussion / Cross-talk": "bold blue",
    }

    def __init__(self, segments: list[TranscriptSegment], max_visible: int = 8):
        self.segments = segments
        self.max_visible = max_visible

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        table = Table.grid(padding=(0, 1))
        table.add_column(style="dim white", width=16)
        table.add_column(width=18)
        table.add_column(ratio=1)

        visible_segments = self.segments[-self.max_visible :]
        if not visible_segments:
            table.add_row("", "", Text("Listening for speech... (speak into mic or play audio)", style="italic dim"))
        else:
            for seg in visible_segments:
                color = self.SPEAKER_COLORS.get(seg.speaker, "bold white")
                table.add_row(
                    seg.formatted_timestamp,
                    Text(seg.speaker, style=color),
                    seg.text,
                )

        yield Panel(table, title="[bold]Live Transcript[/bold]", border_style="blue")
