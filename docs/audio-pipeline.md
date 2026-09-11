# Audio Pipeline Specification

This document describes the audio capture, normalization, and voice activity detection pipeline in VoxLocal.

## Capture Mechanics

VoxLocal interfaces with local audio hardware using the `soundcard` library, which provides cross-platform access to operating system audio subsystems:
- Windows: Windows Audio Session API (WASAPI) with loopback recording.
- macOS: CoreAudio with virtual loopback interfaces such as BlackHole.
- Linux: ALSA or PulseAudio monitor sources.

### WASAPI Loopback Details

On Windows, standard recording APIs only capture input endpoints like microphones. WASAPI loopback allows a client to capture the audio rendering stream of the default output device before it reaches the digital-to-analog converter. 

This means VoxLocal records incoming voices from Zoom, Google Meet, Microsoft Teams, Slack huddles, or browser tabs without requiring virtual cables or audio routing software.

## Dual-Stream Synchronization

Microphone and speaker capture streams operate on independent background threads, writing discrete float32 arrays into synchronization queues.

```
Thread A: Mic Stream      --> Queue(Mic)      ---+
                                                 +--> AudioMixer.pull_mixed_frame()
Thread B: Loopback Stream --> Queue(Loopback) ---+
```

### Channel Normalization

1. Downmixing: Stereo streams are averaged across channels to single-channel mono:
   $$x_{mono}[t] = \frac{x_{left}[t] + x_{right}[t]}{2}$$

2. Resampling: Hardware streams at $f_{in}$ (e.g. 48000 Hz) are resampled using SciPy's Fourier or polyphase filtering to $f_{target} = 16000\text{ Hz}$.

3. Amplitude Normalization: Float32 audio values are clamped to $[-1.0, 1.0]$. Peak amplitude adjustments prevent digital clipping.

## Voice Activity Detection (VAD)

VoxLocal integrates Silero VAD, an ONNX-based neural network trained to classify speech versus non-speech in small time windows.

### Parameter Tuning

- `vad_threshold`: Float between 0.0 and 1.0. Default is 0.5. Higher values require clearer speech before opening the recording gate.
- `window_size_samples`: 512 samples at 16 kHz (32 ms).
- `min_speech_duration_ms`: 250 ms. Brief spikes under this duration, such as keyboard clicks or coughs, are dropped.
- `min_silence_duration_ms`: 300 ms. Speech pauses shorter than this limit remain attached to the active speech phrase.

### Silence Dropping

When speech is detected, the audio frame passes to the sliding ring buffer. When the audio level drops below the threshold for longer than `min_silence_duration_ms`, the gate closes. This prevents idle transcription loops while maintaining speech continuity.
