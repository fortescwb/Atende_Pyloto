"""Agregador de settings base.

Re-exporta todas as settings base para uso externo.
"""

from __future__ import annotations

from config.settings.base.core import (
    BaseSettings,
    Environment,
    get_base_settings,
)
from config.settings.base.dedupe import (
    DedupeBackend,
    DedupeSettings,
    get_dedupe_settings,
)
from config.settings.base.session import (
    SessionSettings,
    SessionStoreBackend,
    get_session_settings,
)

__all__ = [
    # Core
    "BaseSettings",
    "DedupeBackend",
    # Dedupe
    "DedupeSettings",
    # Types
    "Environment",
    # Session
    "SessionSettings",
    "SessionStoreBackend",
    "get_base_settings",
    "get_dedupe_settings",
    "get_session_settings",
]
