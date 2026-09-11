"""Configuration settings for VoxLocal."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AudioConfig(BaseModel):
    """Audio capture and VAD configuration."""

    sample_rate: int = Field(default=16000, description="Target sample rate in Hz (16kHz for Whisper & Silero)")
    mic_device: str | None = Field(default=None, description="Microphone device name or index substring")
    loopback_device: str | None = Field(default=None, description="WASAPI loopback device name or index substring")
    vad_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Silero VAD speech probability threshold")
    min_speech_duration_ms: int = Field(default=250, description="Minimum speech duration to trigger segment")
    min_silence_duration_ms: int = Field(default=300, description="Minimum silence duration to finalize segment")
    frame_duration_ms: int = Field(default=32, description="VAD frame duration in ms (32ms = 512 samples at 16kHz)")


class TranscriptionConfig(BaseModel):
    """Local faster-whisper configuration."""

    model_size: str = Field(default="base.en", description="Whisper model size (tiny.en, base.en, small.en, etc.)")
    compute_type: Literal["int8", "float16", "float32"] = Field(default="int8", description="Quantization format")
    device: Literal["cpu", "cuda", "auto"] = Field(default="cpu", description="Compute device")
    chunk_duration_sec: float = Field(default=3.0, description="Audio chunk duration for streaming transcription")
    chunk_overlap_sec: float = Field(default=0.5, description="Audio chunk overlap in seconds")
    language: str = Field(default="en", description="Transcription language code")
    suppress_hallucinations: bool = Field(default=True, description="Filter common Whisper silence hallucinations")


class SynthesisConfig(BaseModel):
    """Local LLM meeting synthesis and vault export configuration."""

    ollama_url: str = Field(default="http://localhost:11434", description="Ollama API base URL")
    ollama_model: str = Field(default="llama3.2", description="Ollama model name for note synthesis")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0, description="LLM sampling temperature")
    timeout_sec: float = Field(default=60.0, description="Ollama request timeout in seconds")
    default_preset: str = Field(default="general", description="Default meeting template preset")
    vault_dir: Path = Field(default=Path("./meetings"), description="Directory to store Markdown meeting notes")


class VoxLocalSettings(BaseSettings):
    """Master application configuration."""

    model_config = SettingsConfigDict(
        env_prefix="VOXLOCAL_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    audio: AudioConfig = Field(default_factory=AudioConfig)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    synthesis: SynthesisConfig = Field(default_factory=SynthesisConfig)


settings = VoxLocalSettings()
