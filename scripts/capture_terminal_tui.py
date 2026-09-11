"""Render the exact Rich Terminal UI and export it to high-res SVG and PNG."""

import io
from pathlib import Path

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from voxlocal.transcription.whisper_engine import TranscriptSegment
from voxlocal.tui.widgets import AudioVuMeter, TranscriptFeed


def generate_tui_svg():
    buf = io.StringIO()
    console = Console(file=buf, record=True, width=105, height=26, force_terminal=True, color_system="truecolor")

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="meters", size=4),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=3),
    )

    # Header
    title_table = Table.grid(expand=True)
    title_table.add_column(ratio=1)
    title_table.add_column(justify="right")
    title_text = Text()
    title_text.append(" VoxLocal ", style="bold black on cyan")
    title_text.append("  Ambient Audio Copilot: Architecture Sync (Distributed Engine)", style="bold white")
    status_text = Text("● RECORDING (18:42) | Preset: architecture_review ", style="bold green")
    title_table.add_row(title_text, status_text)
    layout["header"].update(Panel(title_table, border_style="cyan"))

    # Audio VU meters
    meter_grid = Table.grid(expand=True)
    meter_grid.add_column(ratio=1)
    meter_grid.add_column(ratio=1)
    meter_grid.add_row(
        AudioVuMeter("Microphone", rms=0.48),
        AudioVuMeter("System Loopback", rms=0.62),
    )
    layout["meters"].update(Panel(meter_grid, title="[bold]Dual-Stream Audio Levels (WASAPI)[/]", border_style="blue"))

    # Transcript feed
    segments = [
        TranscriptSegment(id=1, start=684.0, end=692.0, text="Let's inspect the WASAPI loopback sync between mic and remote streams.", speaker="You", is_bookmarked=False),
        TranscriptSegment(id=2, start=693.0, end=701.0, text="The ring buffer processes 3-second sliding chunks with zero drops during heavy load.", speaker="Remote Speaker 1", is_bookmarked=True),
        TranscriptSegment(id=3, start=702.0, end=709.0, text="Secret redactor masks bearer tokens and AWS keys automatically before disk write.", speaker="You", is_bookmarked=False),
        TranscriptSegment(id=4, start=710.0, end=718.0, text="The SQLite FTS5 search index enables sub-millisecond full-text recall across all vaults.", speaker="Remote Speaker 2", is_bookmarked=True),
        TranscriptSegment(id=5, start=719.0, end=726.0, text="Action item: push the CTranslate2 benchmark results to staging by Friday.", speaker="Remote Speaker 1", is_bookmarked=True),
    ]
    feed = TranscriptFeed(segments=segments, max_visible=6)
    layout["body"].update(Panel(feed, title="[bold]Live Diarized Transcript Feed (⭐ Bookmarked Takeaways)[/]", border_style="green"))

    # Footer
    footer_text = Text()
    footer_text.append("Shortcuts: ", style="bold white")
    footer_text.append("[b] ", style="bold yellow")
    footer_text.append("Bookmark Takeaway (3 marked)  ", style="dim white")
    footer_text.append("[s] ", style="bold cyan")
    footer_text.append("Sync Obsidian  ", style="dim white")
    footer_text.append("[Ctrl+C] ", style="bold red")
    footer_text.append("Finish & Synthesize Notes", style="dim white")
    layout["footer"].update(Panel(footer_text, border_style="dim white"))

    console.print(layout)

    svg_path = Path("docs/images/terminal_tui.svg")
    svg_content = console.export_svg(title="VoxLocal Interactive Terminal HUD")
    svg_path.write_text(svg_content, encoding="utf-8")
    print("Saved SVG to:", svg_path)

if __name__ == "__main__":
    generate_tui_svg()
