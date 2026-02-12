"""Fachada de factories do bootstrap.

Mantém API pública estável enquanto as implementações ficam modularizadas.
"""

from __future__ import annotations

from app.bootstrap.dependencies_services import (
    create_calendar_service,
    create_contact_card_extractor_service,
    create_otto_agent_service,
    create_transcription_service,
)
from app.bootstrap.dependencies_stores import (
    create_async_dedupe_store,
    create_async_session_store,
    create_audit_store,
    create_contact_card_store,
    create_dedupe_store,
    create_session_store,
)

__all__ = [
    "create_async_dedupe_store",
    "create_async_session_store",
    "create_audit_store",
    "create_calendar_service",
    "create_contact_card_extractor_service",
    "create_contact_card_store",
    "create_dedupe_store",
    "create_otto_agent_service",
    "create_session_store",
    "create_transcription_service",
]
