"""Fachada de compatibilidade para modelos de sessão."""

from __future__ import annotations

from app.domain.contact_card import ContactCard
from app.sessions.history import HistoryEntry, HistoryRole
from app.sessions.session_context import SessionContext
from app.sessions.session_entity import Session

__all__ = [
    "ContactCard",
    "HistoryEntry",
    "HistoryRole",
    "Session",
    "SessionContext",
]
