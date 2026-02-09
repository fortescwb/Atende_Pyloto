"""Módulo de sessões para atendimento.

Exporta modelos e gerenciador de sessões.
"""

from app.sessions.manager import DEFAULT_SESSION_TTL_SECONDS, SessionManager
from app.sessions.models import (
    ContactCard,
    HistoryEntry,
    HistoryRole,
    Session,
    SessionContext,
)

__all__ = [
    "DEFAULT_SESSION_TTL_SECONDS",
    "ContactCard",
    "HistoryEntry",
    "HistoryRole",
    "Session",
    "SessionContext",
    "SessionManager",
]
