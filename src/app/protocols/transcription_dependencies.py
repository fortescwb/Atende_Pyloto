"""Protocolos de dependências para transcrição de áudio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.protocols.transcription_service import TranscriptionResult


@dataclass(frozen=True, slots=True)
class MediaDownloadPayload:
    """Resultado mínimo esperado do downloader de mídia."""

    content: bytes | None
    mime_type: str | None
    error: str | None = None


class MediaDownloaderProtocol(Protocol):
    """Contrato para download de mídia do WhatsApp."""

    async def download(
        self,
        *,
        media_id: str | None = None,
        media_url: str | None = None,
    ) -> MediaDownloadPayload:
        """Baixa mídia por ID ou URL."""
        ...


class WhisperClientProtocol(Protocol):
    """Contrato para cliente de transcrição de áudio."""

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str | None,
    ) -> TranscriptionResult:
        """Executa transcrição de áudio."""
        ...
