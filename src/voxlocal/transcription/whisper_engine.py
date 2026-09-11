"""Local speech-to-text engine wrapping faster-whisper (CTranslate2)."""

import logging
import re
from dataclasses import dataclass, field

import numpy as np

from voxlocal.transcription.chunker import AudioChunk

logger = logging.getLogger(__name__)

# Common Whisper hallucinations triggered by low-energy or silent audio frames
KNOWN_HALLUCINATIONS = {
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
    "subscribe to my channel",
    "subtitles by",
    "translated by",
    "you",
    "bye",
    ".",
    "...",
}


@dataclass
class TranscriptWord:
    """Individual word with precise timestamp."""

    word: str
    start: float
    end: float
    probability: float


@dataclass
class TranscriptSegment:
    """Timestamped speech segment attributed to a speaker."""

    id: int
    start: float
    end: float
    text: str
    speaker: str = "Unknown"
    channel: str = "mixed"
    confidence: float = 1.0
    words: list[TranscriptWord] = field(default_factory=list)

    @property
    def formatted_timestamp(self) -> str:
        """Format start and end times as MM:SS."""
        m_start = int(self.start // 60)
        s_start = int(self.start % 60)
        m_end = int(self.end // 60)
        s_end = int(self.end % 60)
        return f"[{m_start:02d}:{s_start:02d} -> {m_end:02d}:{s_end:02d}]"


class WhisperEngine:
    """Performs local, quantized speech-to-text inference with faster-whisper."""

    def __init__(
        self,
        model_size: str = "base.en",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "en",
        suppress_hallucinations: bool = True,
        lazy_load: bool = True,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.suppress_hallucinations = suppress_hallucinations
        self._model = None
        self._segment_counter = 0

        if not lazy_load:
            self._init_model()

    def _init_model(self) -> None:
        """Initialize CTranslate2 Whisper model."""
        if self._model is not None:
            return

        from faster_whisper import WhisperModel

        logger.info(
            "Loading faster-whisper model '%s' on %s (quantization: %s)...",
            self.model_size,
            self.device,
            self.compute_type,
        )
        self._model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )
        logger.info("Whisper model loaded successfully.")

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def is_hallucination(self, text: str, no_speech_prob: float = 0.0) -> bool:
        """Identify repetitive or known silent hallucinations."""
        if not self.suppress_hallucinations:
            return False

        cleaned = re.sub(r"[^\w\s]", "", text.strip().lower())
        if not cleaned or cleaned in KNOWN_HALLUCINATIONS:
            return True

        if no_speech_prob > 0.8:
            return True

        # Check for repetitive loops (e.g. "you you you you")
        words = cleaned.split()
        return bool(len(words) >= 4 and len(set(words)) == 1)

    def transcribe_chunk(
        self,
        chunk: AudioChunk,
        speaker_tag: str | None = None,
    ) -> list[TranscriptSegment]:
        """Transcribe an AudioChunk and return formatted segments.

        Args:
            chunk: AudioChunk containing 16kHz float32 audio.
            speaker_tag: Optional speaker attribution override.

        Returns:
            List of TranscriptSegment instances.
        """
        self._init_model()

        if len(chunk.data) == 0:
            return []

        # Ensure audio values are float32 in [-1, 1]
        audio_data = np.clip(chunk.data, -1.0, 1.0).astype(np.float32)

        segments_out: list[TranscriptSegment] = []
        try:
            raw_segments, _info = self._model.transcribe(
                audio_data,
                language=self.language,
                beam_size=5,
                word_timestamps=True,
                vad_filter=False,  # Audio has already passed Silero VAD
            )

            for raw in raw_segments:
                text = raw.text.strip()
                if self.is_hallucination(text, getattr(raw, "no_speech_prob", 0.0)):
                    continue

                self._segment_counter += 1
                abs_start = chunk.start_time + raw.start
                abs_end = chunk.start_time + raw.end

                words_list = []
                if hasattr(raw, "words") and raw.words:
                    for w in raw.words:
                        words_list.append(
                            TranscriptWord(
                                word=w.word.strip(),
                                start=chunk.start_time + w.start,
                                end=chunk.start_time + w.end,
                                probability=getattr(w, "probability", 1.0),
                            )
                        )

                speaker = speaker_tag or ("You" if chunk.primary_channel == "mic" else "Remote Speaker")
                if chunk.primary_channel == "mixed" and not speaker_tag:
                    speaker = "Mixed / Discussion"

                seg = TranscriptSegment(
                    id=self._segment_counter,
                    start=abs_start,
                    end=abs_end,
                    text=text,
                    speaker=speaker,
                    channel=chunk.primary_channel,
                    confidence=float(np.exp(raw.avg_logprob)) if hasattr(raw, "avg_logprob") else 1.0,
                    words=words_list,
                )
                segments_out.append(seg)

        except Exception as exc:
            logger.error("Error during Whisper transcription: %s", exc)

        return segments_out
