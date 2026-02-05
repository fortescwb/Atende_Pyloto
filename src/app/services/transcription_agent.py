"""TranscriptionAgent — orquestra download + Whisper."""

from __future__ import annotations

import logging

from app.infra.ai.whisper_client import WhisperClient
from app.infra.whatsapp.media_downloader import WhatsAppMediaDownloader
from app.protocols.transcription_service import (
    TranscriptionResult,
    TranscriptionServiceProtocol,
)

logger = logging.getLogger(__name__)

_FALLBACK_TEXT = "audio_nao_transcrito"


class TranscriptionAgent(TranscriptionServiceProtocol):
    """Transcricao de audio do WhatsApp usando Whisper."""

    def __init__(
        self,
        *,
        downloader: WhatsAppMediaDownloader | None = None,
        whisper_client: WhisperClient | None = None,
    ) -> None:
        self._downloader = downloader or WhatsAppMediaDownloader()
        self._whisper = whisper_client or WhisperClient()

    async def transcribe_whatsapp_audio(
        self,
        *,
        media_id: str | None = None,
        media_url: str | None = None,
        mime_type: str | None = None,
        wa_id: str,
    ) -> TranscriptionResult:
        """Transcreve áudio de WhatsApp (media_id preferencial)."""
        if not media_id and not media_url:
            return _fallback("missing_media_reference")

        download_result = await self._downloader.download(
            media_id=media_id,
            media_url=media_url,
        )
        if not download_result.content:
            return _fallback(download_result.error or "download_failed")

        result = await self._whisper.transcribe(
            audio_bytes=download_result.content,
            mime_type=mime_type or download_result.mime_type,
        )

        if result.error:
            return _fallback(result.error)

        return result


def _fallback(error: str | None) -> TranscriptionResult:
    logger.info("transcription_fallback", extra={"reason": error or "unknown"})
    return TranscriptionResult(
        text=_FALLBACK_TEXT,
        confidence=0.0,
        error=error,
    )
