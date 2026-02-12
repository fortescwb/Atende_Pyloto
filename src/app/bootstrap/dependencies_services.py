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


def create_calendar_service() -> Any:
    """Cria GoogleCalendarClient se feature flag habilitada."""
    from app.observability import get_correlation_id
    from config.settings.calendar import get_calendar_settings

    settings = get_calendar_settings()
    if not settings.calendar_enabled:
        logger.info(
            "calendar_service_disabled",
            extra={
                "component": "bootstrap",
                "action": "create_calendar_service",
                "result": "disabled",
                "correlation_id": get_correlation_id(),
            },
        )
        return None
    if not settings.google_calendar_id or not settings.google_service_account_json:
        logger.warning(
            "calendar_service_missing_config",
            extra={
                "component": "bootstrap",
                "action": "create_calendar_service",
                "result": "missing_config",
                "correlation_id": get_correlation_id(),
            },
        )
        return None

    from app.infra.calendar.google_calendar_client import GoogleCalendarClient

    client = GoogleCalendarClient(
        calendar_id=settings.google_calendar_id,
        credentials_json=settings.google_service_account_json,
        timezone=settings.calendar_timezone,
    )
    logger.info(
        "calendar_service_created",
        extra={
            "component": "bootstrap",
            "action": "create_calendar_service",
            "result": "ok",
            "correlation_id": get_correlation_id(),
        },
    )
    return client
