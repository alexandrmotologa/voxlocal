# Configuration Guide

VoxLocal supports configuration via environment variables, CLI flags, or a JSON file located at `~/.voxlocal/config.json`.

## Configuration Precedence

Settings are resolved in the following priority order:
1. Command-line flags (e.g. `--whisper-model small.en`)
2. Environment variables (prefixed with `VOXLOCAL_`)
3. JSON configuration file (`~/.voxlocal/config.json`)
4. Internal defaults

## Settings Reference

```json
{
  "audio": {
    "sample_rate": 16000,
    "mic_device_id": null,
    "loopback_device_id": null,
    "vad_threshold": 0.5,
    "min_speech_duration_ms": 250,
    "min_silence_duration_ms": 300
  },
  "transcription": {
    "whisper_model": "base.en",
    "compute_type": "int8",
    "device": "cpu",
    "chunk_duration_sec": 3.0,
    "chunk_overlap_sec": 0.5,
    "language": "en"
  },
  "synthesis": {
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3.2",
    "temperature": 0.2,
    "timeout_sec": 60,
    "default_preset": "general",
    "vault_dir": "./meetings"
  }
}
```

## Model Size Recommendations

- `tiny.en` (~75 MB RAM): Fast on older dual-core CPUs. Useful for quick tests, but may occasionally misspell technical jargon.
- `base.en` (~145 MB RAM): Recommended default for general developer laptops. Balances low latency with accurate technical vocabulary.
- `small.en` (~480 MB RAM): High accuracy for noisy environments or accented speech.
- `medium.en` (~1.5 GB RAM): Best used on workstations with modern multi-core processors or dedicated GPU acceleration.

## Audio Diagnostics

Run the device discovery command to identify hardware IDs:

```bash
voxlocal devices
```

Output lists system indices for microphones and speakers:

```text
Input Devices (Microphones):
  [0] Default Microphone (Realtek Audio)
  [1] USB Headset Microphone

Loopback Devices (Speakers):
  [0] Default Speakers (Realtek Audio) [WASAPI Loopback]
  [1] HDMI Audio Output
```

To specify explicit devices:

```bash
voxlocal record --mic 1 --loopback 0
```
