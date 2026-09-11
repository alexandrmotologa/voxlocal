"""Command Line Interface for VoxLocal."""

import json
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from voxlocal import __version__
from voxlocal.audio.device import list_loopback_devices, list_microphones
from voxlocal.audio.loopback import LoopbackStreamReader
from voxlocal.audio.mic import MicStreamReader
from voxlocal.audio.resampler import calculate_db
from voxlocal.config import settings
from voxlocal.synthesis.summarizer import Summarizer
from voxlocal.synthesis.vault_writer import VaultWriter
from voxlocal.transcription.whisper_engine import TranscriptSegment
from voxlocal.tui.app import LiveRecordingHUD

app = typer.Typer(
    name="voxlocal",
    help="100% offline ambient audio intelligence and meeting copilot for developers.",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"[bold cyan]VoxLocal[/] version [bold white]{__version__}[/]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True, help="Show version."
    ),
):
    """VoxLocal: Offline meeting assistant and ambient audio copilot."""


@app.command("record")
def record_cmd(
    name: str = typer.Option("Meeting Session", "--name", "-n", help="Title or subject of the meeting."),
    preset: str = typer.Option("general", "--preset", "-p", help="Preset: general, standup, architecture_review, 1on1, client_discovery."),
    mic: str | None = typer.Option(None, "--mic", "-m", help="Microphone device name or ID substring."),
    loopback: str | None = typer.Option(None, "--loopback", "-l", help="Loopback speaker device name or ID substring."),
    whisper_model: str | None = typer.Option(None, "--whisper-model", "-w", help="Whisper model: tiny.en, base.en, small.en, medium.en."),
    ollama_model: str | None = typer.Option(None, "--ollama-model", "-o", help="Ollama model for summarization."),
    vault: Path | None = typer.Option(None, "--vault", help="Target directory for Obsidian / Markdown notes."),
):
    """Start real-time meeting recording and live terminal HUD."""
    hud = LiveRecordingHUD(
        settings=settings,
        meeting_name=name,
        preset=preset,
        mic_device=mic,
        loopback_device=loopback,
        whisper_model=whisper_model,
        ollama_model=ollama_model,
        vault_dir=vault,
    )
    hud.run()


@app.command("devices")
def devices_cmd():
    """List available microphones and system loopback speaker devices."""
    console.print("[bold cyan]VoxLocal Audio Hardware Discovery[/]\n")

    mics = list_microphones()
    mic_table = Table(title="Microphone Inputs (Your Voice)", border_style="cyan")
    mic_table.add_column("Index", style="dim", width=6)
    mic_table.add_column("Name", style="bold white")
    mic_table.add_column("Channels", width=10)
    for m in mics:
        mic_table.add_row(m["index"], m["name"], m["channels"])
    console.print(mic_table)
    console.print()

    loopbacks = list_loopback_devices()
    lb_table = Table(title="Loopback Outputs (Meeting Participants / WASAPI)", border_style="green")
    lb_table.add_column("Index", style="dim", width=6)
    lb_table.add_column("Name", style="bold white")
    lb_table.add_column("Channels", width=10)
    for lb in loopbacks:
        lb_table.add_row(lb["index"], lb["name"], lb["channels"])
    console.print(lb_table)


@app.command("test-audio")
def test_audio_cmd(
    duration: int = typer.Option(5, "--duration", "-d", help="Test duration in seconds."),
    mic: str | None = typer.Option(None, "--mic", "-m", help="Microphone device name or substring."),
    loopback: str | None = typer.Option(None, "--loopback", "-l", help="Loopback device name or substring."),
):
    """Verify microphone and loopback audio levels with live RMS reporting."""
    console.print(f"[bold cyan]Testing audio devices for {duration} seconds...[/]")
    console.print("[dim]Speak into your microphone and play audio through your speakers.\n[/]")

    mic_peaks = []
    loopback_peaks = []

    def on_mic(samples, rms):
        mic_peaks.append(rms)

    def on_lb(samples, rms):
        loopback_peaks.append(rms)

    mic_reader = MicStreamReader(device_name_or_id=mic, callback=on_mic)
    lb_reader = LoopbackStreamReader(device_name_or_id=loopback, callback=on_lb)

    mic_reader.start()
    lb_reader.start()

    try:
        with console.status("[bold green]Listening for audio activity...[/]") as status:
            for remaining in range(duration, 0, -1):
                status.update(f"[bold green]Listening... ({remaining}s remaining)[/]")
                time.sleep(1.0)
    finally:
        mic_reader.stop()
        lb_reader.stop()

    max_mic = max(mic_peaks) if mic_peaks else 0.0
    max_lb = max(loopback_peaks) if loopback_peaks else 0.0

    table = Table(title="Audio Test Results", border_style="cyan")
    table.add_column("Device", style="bold")
    table.add_column("Peak RMS")
    table.add_column("Peak dBFS")
    table.add_column("Status")

    mic_status = "[bold green]Active (Sound detected)[/]" if max_mic > 0.005 else "[yellow]Quiet / No sound[/]"
    lb_status = "[bold green]Active (Sound detected)[/]" if max_lb > 0.005 else "[yellow]Quiet / No sound[/]"

    table.add_row(f"Mic ({mic_reader.device_name})", f"{max_mic:.4f}", f"{calculate_db(max_mic):.1f} dB", mic_status)
    table.add_row(f"Loopback ({lb_reader.device_name})", f"{max_lb:.4f}", f"{calculate_db(max_lb):.1f} dB", lb_status)

    console.print(table)


@app.command("summarize")
def summarize_cmd(
    transcript_file: Path = typer.Argument(..., help="Path to text or JSON transcript file."),
    title: str = typer.Option("Meeting Summary", "--title", "-t", help="Meeting title."),
    preset: str = typer.Option("general", "--preset", "-p", help="Prompt preset: general, standup, architecture_review, 1on1, client_discovery."),
    out: Path | None = typer.Option(None, "--out", "-o", help="Custom output Markdown file path."),
    vault_dir: Path | None = typer.Option(None, "--vault", help="Vault directory if out is not specified."),
):
    """Generate structured Markdown notes from an existing transcript file."""
    if not transcript_file.exists():
        console.print(f"[bold red]File not found:[/] {transcript_file}")
        raise typer.Exit(code=1)

    raw_text = transcript_file.read_text(encoding="utf-8")
    segments = []

    # Check if JSON format
    try:
        data = json.loads(raw_text)
        if isinstance(data, list):
            for idx, item in enumerate(data):
                segments.append(
                    TranscriptSegment(
                        id=idx + 1,
                        start=item.get("start", 0.0),
                        end=item.get("end", 0.0),
                        text=item.get("text", ""),
                        speaker=item.get("speaker", "Unknown"),
                    )
                )
    except Exception:
        # Line-by-line format
        for idx, line in enumerate(raw_text.splitlines()):
            line = line.strip()
            if line:
                segments.append(
                    TranscriptSegment(
                        id=idx + 1,
                        start=idx * 2.0,
                        end=(idx + 1) * 2.0,
                        text=line,
                        speaker="Speaker",
                    )
                )

    summarizer = Summarizer(
        ollama_url=settings.synthesis.ollama_url,
        model_name=settings.synthesis.ollama_model,
    )

    console.print(f"[bold cyan]Synthesizing notes for '{title}' (preset: {preset})...[/]")
    summary_md = summarizer.summarize(segments, title=title, preset=preset)

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(summary_md, encoding="utf-8")
        console.print(f"[bold green]Saved notes to:[/] {out.resolve()}")
    else:
        v_dir = vault_dir or settings.synthesis.vault_dir
        writer = VaultWriter(vault_dir=v_dir)
        saved_file = writer.write_meeting_note(
            title=title,
            summary_markdown=summary_md,
            segments=segments,
            speaker_stats={},
            preset=preset,
        )
        console.print(f"[bold green]Saved notes to vault:[/] {saved_file.resolve()}")


@app.command("config")
def config_cmd(
    init: bool = typer.Option(False, "--init", help="Create initial config file at ~/.voxlocal/config.json."),
):
    """View or initialize VoxLocal settings."""
    cfg_path = Path.home() / ".voxlocal" / "config.json"
    if init:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        dump_data = settings.model_dump(mode="json")
        cfg_path.write_text(json.dumps(dump_data, indent=2), encoding="utf-8")
        console.print(f"[bold green]Initialized config file at:[/] {cfg_path}")
        return

    console.print(
        Panel(
            json.dumps(settings.model_dump(mode="json"), indent=2),
            title="[bold cyan]Active VoxLocal Configuration[/bold cyan]",
            border_style="cyan",
        )
    )


if __name__ == "__main__":
    app()
