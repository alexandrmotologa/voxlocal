# VoxLocal

100% offline ambient audio intelligence and meeting copilot for developers.

VoxLocal captures microphone input and system speaker loopback concurrently, transcribes speech locally in sub-seconds with quantized Whisper, attributes speakers, and writes structured Markdown meeting summaries directly into your local vault. It requires zero cloud connections and operates with no telemetry.

## Why VoxLocal

Cloud meeting assistants require bots that join calls, send private corporate conversations to third-party servers, and trigger privacy or compliance concerns. 

VoxLocal runs entirely on your local machine. It captures audio at the driver layer through Windows WASAPI or macOS CoreAudio, processes audio through local neural models, and talks to your local Ollama or Llama.cpp instance. Your voice and your colleagues' audio never leave your computer.

```
+------------------+     +------------------------+
| Microphone (You) |     | System Audio (Colleagues)|
+--------+---------+     +-----------+------------+
         |                           |
         +-------------+-------------+
                       |
               [Audio Mixer 16kHz]
                       |
               [Silero VAD Gating]
                       |
             [Audio Ring Buffer]
                       |
        [faster-whisper / CTranslate2]
                       |
         [Hardware Speaker Tagging]
         (Channel 0: You | Channel 1: Remote)
                       |
         [Local Synthesis (Ollama)]
         (Executive Summary, Actions, Notes)
                       |
        [Obsidian / Markdown Vault]
```

## Features

- Dual-stream audio capture: Records your microphone and system output loopback simultaneously.
- Zero bot intrusion: Operates silently at the OS audio driver level without joining meetings as a participant.
- Voice activity filtering: Silero VAD prunes silence, keystrokes, and background noise before inference.
- Fast local transcription: Uses faster-whisper and CTranslate2 with INT8 quantization for sub-second streaming latency on CPU or GPU.
- Speaker attribution: Distinguishes your microphone input from remote call participants based on audio stream source.
- PII and secret redaction: Automatically sanitizes API keys, tokens, passwords, and personal information before saving notes.
- Live bookmarking: Flag critical moments during meetings with key takeaways highlighted in final notes.
- Local LLM notes synthesis: Connects to local Ollama or Llama.cpp servers to produce executive summaries, key decisions, and action items with assignees.
- Offline extractive fallback: If your local LLM daemon is offline, VoxLocal generates structured notes using an internal rule-based parser so records are preserved.
- Knowledge base search and Q&A: Fast local full-text search (SQLite FTS5) across past meetings with `voxlocal search` and natural language Q&A with `voxlocal ask`.
- Obsidian and Git automation: Automatically opens new notes in Obsidian (`--open-obsidian`) and commits them to Git (`--git-commit`).
- Audio archiving: Optionally archives 16kHz WAV audio alongside meeting notes (`--save-audio`).
- Companion web dashboard: Real-time browser HUD (`voxlocal serve`) with live waveforms, transcript feed, and quick-copy tools.
- Background hotkey daemon: Start and stop recording anywhere with `Win+Alt+R` and desktop toast notifications (`voxlocal daemon`).

## Installation

### Prerequisites

- Python 3.12 or newer
- Git
- Optional: Ollama running locally (`ollama run llama3.2`)

### Install with uv or pip

```bash
# Clone the repository
git clone https://github.com/alexandrmotologa/voxlocal.git
cd voxlocal

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

## Quick Start

### 1. Check audio devices

List available input microphones and system loopback output devices:

```bash
voxlocal devices
```

### 2. Verify audio levels

Test that both your microphone and loopback audio streams receive sound:

```bash
voxlocal test-audio --duration 5
```

### 3. Start a meeting session

Launch the live recording HUD:

```bash
voxlocal record --name "Architecture Discussion" --preset architecture_review
```

During the meeting, the terminal displays:
- Live VU level meters for your microphone and remote participants
- Real-time timestamped speech transcript
- Memory and processing status

Press `Ctrl+C` to end the session. VoxLocal stops recording, runs local synthesis, and saves the Markdown file to your vault.

### 4. Summarize an existing transcript

If you already have a transcript JSON file:

```bash
voxlocal summarize transcript.json --preset standup --out notes.md
```

## Meeting Presets

VoxLocal includes prompt presets tailored to common technical meetings:

- `general`: Standard meeting overview, agenda items, decisions, and follow-ups.
- `standup`: Focuses on completed tasks, current blockers, and today's planned goals.
- `architecture_review`: Catalogs proposed designs, trade-offs, consensus decisions, and migration steps.
- `1on1`: Tracks project alignment, feedback items, career goals, and personal action items.
- `client_discovery`: Highlights client requirements, pain points, constraints, and agreed timelines.

## Configuration

VoxLocal reads configuration from environment variables or a configuration file located at `~/.voxlocal/config.json`.

Generate a default configuration:

```bash
voxlocal config --init
```

Key configuration options:

| Setting | Default | Description |
| :--- | :--- | :--- |
| `whisper_model` | `base.en` | Whisper model size (`tiny.en`, `base.en`, `small.en`, `medium.en`) |
| `compute_type` | `int8` | Inference quantization (`int8`, `float16`, `float32`) |
| `vad_threshold` | `0.5` | Silero voice activity detection sensitivity (0.1 to 0.9) |
| `ollama_url` | `http://localhost:11434` | Local Ollama API endpoint |
| `ollama_model` | `llama3.2` | Model name for meeting summary generation |
| `vault_dir` | `./meetings` | Destination folder for generated Markdown notes |
| `default_preset` | `general` | Default template for notes synthesis |

## Running with Docker

Run VoxLocal in a container for headless audio processing:

```bash
docker compose up -d
```

## Testing

Run the test suite, including synthetic audio capture and VAD tests:

```bash
pytest -v
```

## Architecture Documentation

For in-depth explanations of individual subsystems, inspect the guides in `docs/`:

- [Architecture Overview](docs/architecture.md)
- [Audio Capture and Synchronization Pipeline](docs/audio-pipeline.md)
- [Configuration and Hardware Guide](docs/configuration.md)
- [Prompt Engineering and Markdown Vaults](docs/prompts-and-vault.md)

## License

MIT License. See [LICENSE](LICENSE) for details.
