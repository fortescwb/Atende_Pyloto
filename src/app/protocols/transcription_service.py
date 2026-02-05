"""Protocolo para transcricao de audio (WhatsApp)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    """Resultado da transcricao de audio."""

    text: str
    language: str | None = None
    duration_seconds: float | None = None
    confidence: float = 0.0
    error: str | None = None


class TranscriptionServiceProtocol(Protocol):
    """Contrato para transcricao de audio do WhatsApp."""

    async def transcribe_whatsapp_audio(
        self,
        *,
        media_id: str | None = None,
        media_url: str | None = None,
        mime_type: str | None = None,
        wa_id: str,
    ) -> TranscriptionResult:
        """Transcreve audio de WhatsApp e retorna resultado."""
        ...
