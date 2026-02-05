"""Cliente Whisper (OpenAI) para transcricao de audio."""

from __future__ import annotations

import io
import logging
from typing import Any

from openai import AsyncOpenAI

from app.protocols.transcription_service import TranscriptionResult
from config.settings.ai.openai import OpenAISettings, get_openai_settings

logger = logging.getLogger(__name__)


_MIME_EXT_MAP = {
    "audio/ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/ogg; codecs=opus": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".mp4",
    "audio/aac": ".aac",
}


class WhisperClient:
    """Cliente para transcricao com Whisper API."""

    __slots__ = ("_client", "_timeout_seconds")

    def __init__(
        self,
        *,
        settings: OpenAISettings | None = None,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
        client: AsyncOpenAI | None = None,
    ) -> None:
        cfg = settings or get_openai_settings()
        self._timeout_seconds = float(timeout_seconds or min(cfg.timeout_seconds, 8.0))
        if client is not None:
            self._client = client
        else:
            self._client = AsyncOpenAI(
                api_key=api_key or cfg.api_key,
                timeout=self._timeout_seconds,
            )

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str | None = None,
    ) -> TranscriptionResult:
        """Transcreve audio em texto usando Whisper (whisper-1)."""
        if not audio_bytes:
            return TranscriptionResult(text="", confidence=0.0, error="empty_audio")

        extension = _MIME_EXT_MAP.get((mime_type or "").lower(), ".ogg")
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"audio{extension}"

        # Whisper aceita OGG/Opus; conversao so se necessario (nao aplicada aqui).
        try:
            response = await self._client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
            )
        except Exception as exc:
            logger.warning(
                "whisper_transcription_failed",
                extra={"error_type": type(exc).__name__},
            )
            return TranscriptionResult(text="", confidence=0.0, error="whisper_failed")

        data = _to_dict(response)
        text = str(data.get("text") or "").strip()
        language = data.get("language")
        segments = data.get("segments") if isinstance(data.get("segments"), list) else []

        duration_seconds = _extract_duration(data, segments)
        confidence = _estimate_confidence(text, segments)

        return TranscriptionResult(
            text=text,
            language=language,
            duration_seconds=duration_seconds,
            confidence=confidence,
            error=None,
        )


def _to_dict(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if hasattr(response, "dict"):
        return response.dict()
    return {}


def _extract_duration(data: dict[str, Any], segments: list[Any]) -> float | None:
    duration = data.get("duration")
    if isinstance(duration, (int, float)):
        return float(duration)

    max_end = None
    for seg in segments:
        end = None
        if isinstance(seg, dict):
            end = seg.get("end")
        elif hasattr(seg, "end"):
            end = seg.end
        if isinstance(end, (int, float)):
            max_end = max(max_end or 0.0, float(end))

    return max_end


def _estimate_confidence(text: str, segments: list[Any]) -> float:
    if not text:
        return 0.0

    scores: list[float] = []
    for seg in segments:
        avg_logprob = None
        if isinstance(seg, dict):
            avg_logprob = seg.get("avg_logprob")
        elif hasattr(seg, "avg_logprob"):
            avg_logprob = seg.avg_logprob

        if isinstance(avg_logprob, (int, float)):
            score = max(0.0, min(1.0, 1.0 + float(avg_logprob)))
            scores.append(score)

    if scores:
        return sum(scores) / len(scores)

    return 0.5
