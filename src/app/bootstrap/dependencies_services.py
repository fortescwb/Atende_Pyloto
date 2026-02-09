"""Factories de serviços da camada AI e utilitários associados."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def create_otto_agent_service() -> Any:
    """Cria OttoAgentService com client OpenAI configurado."""
    from ai.services.otto_agent import OttoAgentService
    from app.infra.ai.otto_client import OttoClient

    client = OttoClient()
    service = OttoAgentService(client=client)
    logger.info("otto_agent_service_created")
    return service


def create_contact_card_extractor_service() -> Any:
    """Cria ContactCardExtractorService com client OpenAI."""
    from ai.services.contact_card_extractor import ContactCardExtractorService
    from app.infra.ai.contact_card_extractor_client import ContactCardExtractorClient

    client = ContactCardExtractorClient()
    service = ContactCardExtractorService(client=client)
    logger.info("contact_card_extractor_service_created")
    return service


def create_transcription_service() -> Any:
    """Cria TranscriptionAgent com dependências padrão."""
    from app.infra.ai.whisper_client import WhisperClient
    from app.infra.whatsapp.media_downloader import WhatsAppMediaDownloader
    from app.services.transcription_agent import TranscriptionAgent

    service = TranscriptionAgent(
        downloader=WhatsAppMediaDownloader(),
        whisper_client=WhisperClient(),
    )
    logger.info("transcription_service_created")
    return service
