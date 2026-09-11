# VoxLocal Architecture

This document details the internal design of VoxLocal, an offline ambient audio intelligence system.

## System Overview

VoxLocal runs as a local background daemon or interactive terminal application. It captures two independent audio channels from the host operating system, aligns them in time, discards non-speech periods, transcribes audio frames using local quantized neural models, and synthesizes structured Markdown meeting notes.

```
+-------------------------------------------------------------------+
|                        Operating System Audio                     |
|                                                                   |
|   Microphone (Local User)          System Audio Output (WASAPI)   |
+-------------------+------------------------------+----------------+
                    |                              |
                    v                              v
           [MicStreamReader]             [LoopbackStreamReader]
                    \                              /
                     \                            /
                      v                          v
             +--------------------------------------------+
             |           DualChannelAudioMixer            |
             |  - Resamples to 16 kHz mono float32        |
             |  - Time-aligns local and loopback buffers  |
             |  - Maintains hardware channel metadata     |
             +---------------------+----------------------+
                                   |
                                   v
             +--------------------------------------------+
             |             Silero VAD Engine              |
             |  - Evaluates speech probability per chunk  |
             |  - Prunes silence, keystrokes, background  |
             +---------------------+----------------------+
                                   | (Speech chunks only)
                                   v
             +--------------------------------------------+
             |           Streaming Audio Chunker          |
             |  - 3-second sliding ring buffer            |
             |  - 500 ms boundary overlap protection      |
             +---------------------+----------------------+
                                   |
                                   v
             +--------------------------------------------+
             |         Whisper Transcription Engine       |
             |  - CTranslate2 INT8 model inference        |
             |  - Word timestamps and probability scoring |
             +---------------------+----------------------+
                                   |
                                   v
             +--------------------------------------------+
             |          Speaker Attribution Lite          |
             |  - Channel 0 mapped to "You"               |
             |  - Channel 1 mapped to "Remote Speaker"    |
             |  - Energy clustering for remote voices     |
             +---------------------+----------------------+
                                   |
                                   v
             +--------------------------------------------+
             |               LLM Synthesizer              |
             |  - Local Ollama / Llama.cpp REST client    |
             |  - Deterministic extractive fallback       |
             |  - Action items, decisions, summary        |
             +---------------------+----------------------+
                                   |
                                   v
             +--------------------------------------------+
             |              Vault Markdown Writer         |
             |  - Obsidian YAML frontmatter format        |
             |  - Writes to target vault directory        |
             +--------------------------------------------+
```

## Core Subsystems

### 1. Dual-Stream Audio Capture
Windows WASAPI loopback allows recording the mixed output of all desktop applications, such as Zoom, Teams, and Slack. Simultaneously, the microphone capture thread records the user's local voice. Both streams are read into thread-safe queues.

### 2. Audio Synchronizer and Resampler
Hardware audio devices report different native sample rates (typically 44100 Hz or 48000 Hz). The resampler converts both streams to 16000 Hz float32 mono, matching Whisper and Silero VAD input standards. The mixer pairs corresponding chunks from both streams.

### 3. Voice Activity Detection (VAD)
Sending silent or noisy audio to Whisper wastes CPU cycles and induces hallucinations. Silero VAD evaluates 30 ms to 60 ms audio windows, discarding frames with speech probability below 0.5.

### 4. Streaming Chunker
Audio accumulates in a sliding ring buffer. When accumulated speech reaches the configured chunk size (default 3 seconds), it is dispatched to the transcription engine. A 500 ms overlap prevents word clipping at chunk boundaries.

### 5. Local Whisper Transcription
The transcription module uses `faster-whisper`, a CTranslate2 implementation of OpenAI's Whisper models. On a standard modern CPU, the INT8-quantized `base.en` model processes 3-second audio slices in under 200 ms, keeping the transcription pipeline comfortably faster than real time.

### 6. Hardware-Based Diarization
Most diarization systems require heavy neural speaker embeddings. VoxLocal achieves high speaker accuracy by using physical audio channels:
- Sounds from the microphone originate from the local user ("You").
- Sounds from the loopback interface originate from remote meeting participants ("Remote").
- For remote participants, acoustic energy clustering identifies secondary speakers.

### 7. Synthesis and Vault Persistence
At meeting completion, the accumulated timestamped transcript passes to the synthesis module. The module queries a local Ollama instance running Llama 3.2 or Mistral. If the model server is offline, VoxLocal applies an extractive rule-based parser that identifies task checkboxes and key decisions, formatting the final document into Obsidian-compatible Markdown.
