"""Terminal User Interface dashboard orchestrating live meeting recording."""

import time
from datetime import datetime
from pathlib import Path

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from voxlocal.audio.archiver import AudioArchiver
from voxlocal.audio.loopback import LoopbackStreamReader
from voxlocal.audio.mic import MicStreamReader
from voxlocal.audio.mixer import DualChannelAudioMixer
from voxlocal.audio.vad import VoiceActivityDetector
from voxlocal.config import VoxLocalSettings
from voxlocal.daemon.notify import send_notification
from voxlocal.synthesis.summarizer import Summarizer
from voxlocal.synthesis.vault_writer import VaultWriter, format_duration
from voxlocal.transcription.chunker import StreamingAudioChunker
from voxlocal.transcription.diarization import SpeakerDiarizer
from voxlocal.transcription.whisper_engine import TranscriptSegment, WhisperEngine
from voxlocal.tui.widgets import AudioVuMeter, TranscriptFeed
from voxlocal.web.server import SharedWebState


class LiveRecordingHUD:
    """Terminal recording HUD displaying real-time meters and transcript feed."""

    def __init__(
        self,
        settings: VoxLocalSettings,
        meeting_name: str = "Meeting Session",
        preset: str = "general",
        mic_device: str | None = None,
        loopback_device: str | None = None,
        whisper_model: str | None = None,
        ollama_model: str | None = None,
        vault_dir: Path | None = None,
        save_audio: bool = False,
        open_obsidian: bool = False,
        git_commit: bool = False,
    ):
        self.settings = settings
        self.meeting_name = meeting_name
        self.preset = preset
        self.mic_device_id = mic_device or settings.audio.mic_device
        self.loopback_device_id = loopback_device or settings.audio.loopback_device
        self.whisper_model_size = whisper_model or settings.transcription.model_size
        self.ollama_model_name = ollama_model or settings.synthesis.ollama_model
        self.vault_dir = vault_dir or settings.synthesis.vault_dir
        self.save_audio = save_audio
        self.open_obsidian = open_obsidian
        self.git_commit = git_commit

        self.console = Console()
        self.segments: list[TranscriptSegment] = []
        self._running = False
        self._start_time = None

        # Core subsystems
        self.mixer = DualChannelAudioMixer(target_sr=settings.audio.sample_rate)
        self.vad = VoiceActivityDetector(
            threshold=settings.audio.vad_threshold,
            min_speech_duration_ms=settings.audio.min_speech_duration_ms,
            min_silence_duration_ms=settings.audio.min_silence_duration_ms,
            sample_rate=settings.audio.sample_rate,
        )
        self.chunker = StreamingAudioChunker(
            sample_rate=settings.audio.sample_rate,
            chunk_duration_sec=settings.transcription.chunk_duration_sec,
            overlap_sec=settings.transcription.chunk_overlap_sec,
            vad_detector=self.vad,
        )
        self.whisper = WhisperEngine(
            model_size=self.whisper_model_size,
            device=settings.transcription.device,
            compute_type=settings.transcription.compute_type,
            language=settings.transcription.language,
            suppress_hallucinations=settings.transcription.suppress_hallucinations,
            lazy_load=True,
        )
        self.diarizer = SpeakerDiarizer(local_user_name="You")
        self.summarizer = Summarizer(
            ollama_url=settings.synthesis.ollama_url,
            model_name=self.ollama_model_name,
            temperature=settings.synthesis.temperature,
            timeout_sec=settings.synthesis.timeout_sec,
        )
        self.vault_writer = VaultWriter(vault_dir=self.vault_dir)

        # Readers
        self.mic_reader = MicStreamReader(
            device_name_or_id=self.mic_device_id,
            target_sr=settings.audio.sample_rate,
            callback=self.mixer.on_mic_data,
        )
        self.loopback_reader = LoopbackStreamReader(
            device_name_or_id=self.loopback_device_id,
            target_sr=settings.audio.sample_rate,
            callback=self.mixer.on_loopback_data,
        )

    def _render_layout(self) -> Group:
        """Construct the composite Rich UI layout."""
        elapsed = time.time() - self._start_time if self._start_time else 0.0
        mic_rms, loopback_rms = self.mixer.current_rms_levels

        # Header Table
        header_table = Table.grid(expand=True)
        header_table.add_column(ratio=1)
        header_table.add_column(justify="right")
        header_table.add_row(
            Text.from_markup(f"[bold white]{self.meeting_name}[/] [dim]({self.preset})[/]"),
            Text(f"Elapsed: {format_duration(elapsed)}", style="bold green"),
        )
        header_panel = Panel(header_table, style="dim white", border_style="cyan")

        # Audio Meters Table
        meters_table = Table.grid(expand=True, padding=(0, 2))
        meters_table.add_column(ratio=1)
        meters_table.add_column(ratio=1)
        meters_table.add_row(
            AudioVuMeter(label="Mic (You)", rms=mic_rms),
            AudioVuMeter(label="Loopback", rms=loopback_rms),
        )
        meters_panel = Panel(meters_table, title="[bold]Audio Levels[/bold]", border_style="green")

        # Transcript Feed
        feed_widget = TranscriptFeed(self.segments, max_visible=6)

        # Status Bar
        status_text = Text()
        status_text.append(f"Segments: {len(self.segments)} | ", style="dim")
        status_text.append(f"Model: {self.whisper_model_size} | ", style="dim")
        status_text.append("Press Ctrl+C to finish & synthesize notes", style="bold yellow")
        status_panel = Panel(status_text, style="dim")

        return Group(header_panel, meters_panel, feed_widget, status_panel)

    def run(self) -> Path | None:
        """Run the live HUD recording loop until KeyboardInterrupt."""
        self.console.clear()
        self.console.print("[bold cyan]VoxLocal[/] v0.1.0 — Initializing audio capture...\n")
        self.console.print(f"[dim]Microphone: {self.mic_reader.device_name}[/]")
        self.console.print(f"[dim]Loopback:   {self.loopback_reader.device_name}[/]\n")
        self._running = True
        self._start_time = time.time()
        start_datetime = datetime.now()

        # Audio archiver
        archiver = AudioArchiver(target_dir=self.vault_dir / ".audio") if self.save_audio else None

        # Update SharedWebState
        SharedWebState.is_recording = True
        SharedWebState.meeting_name = self.meeting_name
        SharedWebState.preset = self.preset
        SharedWebState.segments = []
        SharedWebState.bookmarks_count = 0

        # Start audio capture threads
        self.mic_reader.start()
        self.loopback_reader.start()

        send_notification("VoxLocal Started", f"Recording '{self.meeting_name}' ({self.preset})")

        try:
            with Live(self._render_layout(), refresh_per_second=8, console=self.console) as live:
                while self._running:
                    # Pull mixed audio frames
                    frame = self.mixer.pull_frame(timeout=0.05)
                    if frame is not None:
                        self.chunker.add_frame(frame)
                        if archiver:
                            archiver.add_frame(frame)

                    # Extract chunk for transcription if buffer is ready
                    chunk = self.chunker.extract_chunk()
                    if chunk is not None:
                        speaker = self.diarizer.attribute_speaker(chunk, sample_rate=self.settings.audio.sample_rate)
                        new_segments = self.whisper.transcribe_chunk(chunk, speaker_tag=speaker)
                        for seg in new_segments:
                            self.segments.append(seg)
                            self.diarizer.record_words(seg.speaker, len(seg.text.split()))

                    # Update Web state
                    m_rms, lb_rms = self.mixer.current_rms_levels
                    SharedWebState.mic_rms = m_rms
                    SharedWebState.loopback_rms = lb_rms
                    SharedWebState.elapsed_sec = time.time() - self._start_time
                    SharedWebState.segments = [
                        {
                            "speaker": s.speaker,
                            "text": s.text,
                            "formatted_timestamp": s.formatted_timestamp,
                            "is_bookmarked": getattr(s, "is_bookmarked", False),
                        }
                        for s in self.segments
                    ]

                    live.update(self._render_layout())
                    time.sleep(0.01)

        except KeyboardInterrupt:
            self.console.print("\n[bold yellow]Stopping audio recording...[/]")
        finally:
            self._running = False
            SharedWebState.is_recording = False
            self.mic_reader.stop()
            self.loopback_reader.stop()

        duration = time.time() - self._start_time

        # Flush any remaining audio in chunker
        final_chunk = self.chunker.flush()
        if final_chunk is not None:
            speaker = self.diarizer.attribute_speaker(final_chunk, sample_rate=self.settings.audio.sample_rate)
            new_segments = self.whisper.transcribe_chunk(final_chunk, speaker_tag=speaker)
            for seg in new_segments:
                self.segments.append(seg)
                self.diarizer.record_words(seg.speaker, len(seg.text.split()))

        # Save audio if requested
        saved_audio_path = None
        if archiver:
            from voxlocal.synthesis.vault_writer import slugify_title
            saved_audio_path = archiver.save(f"{start_datetime.strftime('%Y-%m-%d')}_{slugify_title(self.meeting_name)}")
            if saved_audio_path:
                self.console.print(f"[dim]Saved meeting audio to: {saved_audio_path}[/]")

        self.console.print("[bold green]Generating Markdown notes with synthesis engine...[/]")
        summary_md = self.summarizer.summarize(
            self.segments,
            title=self.meeting_name,
            preset=self.preset,
            local_user="You",
        )

        note_path = self.vault_writer.write_meeting_note(
            title=self.meeting_name,
            summary_markdown=summary_md,
            segments=self.segments,
            speaker_stats=self.diarizer.speaker_stats,
            preset=self.preset,
            start_time=start_datetime,
            duration_sec=duration,
            audio_path=saved_audio_path,
            open_in_obsidian=self.open_obsidian,
            git_commit=self.git_commit,
        )

        send_notification("VoxLocal Notes Saved", f"Saved to {note_path.name}")

        # Print success summary
        self.console.print(
            Panel(
                f"[bold green]Meeting notes saved successfully![/]\n\n"
                f"[cyan]File:[/] [bold]{note_path.resolve()}[/]\n"
                f"[cyan]Duration:[/] {format_duration(duration)}\n"
                f"[cyan]Transcribed Turns:[/] {len(self.segments)}\n"
                f"[cyan]Talk-time Summary:[/] {self.diarizer.get_talk_time_summary()}",
                title="[bold]VoxLocal Session Complete[/bold]",
                border_style="green",
            )
        )
        return note_path
