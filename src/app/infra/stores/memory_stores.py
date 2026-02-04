"""Stores em memória — apenas para desenvolvimento e testes.

ATENÇÃO: Não usar em staging/production. Sem persistência entre reinícios.
"""

from __future__ import annotations

import json
import time
from typing import Any

from app.protocols.decision_audit_store import DecisionAuditStoreProtocol
from app.protocols.dedupe import AsyncDedupeProtocol, DedupeProtocol
from app.protocols.session_store import AsyncSessionStoreProtocol, SessionStoreProtocol
from app.sessions.models import Session


class MemorySessionStore(SessionStoreProtocol, AsyncSessionStoreProtocol):
    """Store de sessão em memória — apenas para dev/test."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float]] = {}  # session_id -> (json, expires_at)

    def _save_sync(self, session: Any, ttl_seconds: int = 7200) -> None:
        """Implementação sync de save."""
        if isinstance(session, Session):
            data = json.dumps(session.to_dict())
            session_id = session.session_id
        else:
            data = json.dumps(session)
            session_id = session.get("session_id", str(id(session)))
        expires_at = time.time() + ttl_seconds
        self._store[session_id] = (data, expires_at)

    def _load_sync(self, session_id: str) -> Session | None:
        """Implementação sync de load."""
        entry = self._store.get(session_id)
        if entry is None:
            return None
        data, expires_at = entry
        if time.time() > expires_at:
            del self._store[session_id]
            return None
        return Session.from_dict(json.loads(data))

    def _delete_sync(self, session_id: str) -> bool:
        """Implementação sync de delete."""
        if session_id in self._store:
            del self._store[session_id]
            return True
        return False

    def _exists_sync(self, session_id: str) -> bool:
        """Implementação sync de exists."""
        entry = self._store.get(session_id)
        if entry is None:
            return False
        _, expires_at = entry
        if time.time() > expires_at:
            del self._store[session_id]
            return False
        return True

    # Sync API (protocolo SessionStoreProtocol)
    def save(self, session: Any, ttl_seconds: int = 7200) -> None:  # type: ignore[override]
        """Salva sessão em memória."""
        return self._save_sync(session, ttl_seconds)

    def load(self, session_id: str) -> Session | None:  # type: ignore[override]
        """Carrega sessão da memória."""
        return self._load_sync(session_id)

    def delete(self, session_id: str) -> bool:  # type: ignore[override]
        """Remove sessão da memória."""
        return self._delete_sync(session_id)

    def exists(self, session_id: str) -> bool:  # type: ignore[override]
        """Verifica se sessão existe."""
        return self._exists_sync(session_id)

    # Async API (protocolo AsyncSessionStoreProtocol)
    async def save_async(self, session: Any, ttl_seconds: int = 7200) -> None:
        """Salva sessão em memória (async wrapper)."""
        self._save_sync(session, ttl_seconds)

    async def load_async(self, session_id: str) -> Session | None:
        """Carrega sessão da memória (async wrapper)."""
        return self._load_sync(session_id)

    async def delete_async(self, session_id: str) -> bool:
        """Remove sessão da memória (async wrapper)."""
        return self._delete_sync(session_id)

    async def exists_async(self, session_id: str) -> bool:
        """Verifica se sessão existe (async wrapper)."""
        return self._exists_sync(session_id)


class MemoryDedupeStore(DedupeProtocol, AsyncDedupeProtocol):
    """Store de dedupe em memória — apenas para dev/test."""

    def __init__(self) -> None:
        self._store: dict[str, float] = {}  # key -> expires_at

    def _cleanup_expired(self) -> None:
        """Remove entradas expiradas."""
        now = time.time()
        expired = [k for k, v in self._store.items() if v < now]
        for k in expired:
            del self._store[k]

    def seen(self, key: str, ttl: int) -> bool:
        """Verifica e marca chave atomicamente (sync)."""
        self._cleanup_expired()
        now = time.time()
        if key in self._store and self._store[key] > now:
            return True  # Duplicado
        self._store[key] = now + ttl
        return False  # Novo

    async def is_duplicate(self, key: str, ttl: int = 3600) -> bool:
        """Verifica se chave já foi processada (async)."""
        self._cleanup_expired()
        now = time.time()
        return key in self._store and self._store[key] > now

    async def mark_processed(self, key: str, ttl: int = 3600) -> None:
        """Marca chave como processada (async)."""
        self._store[key] = time.time() + ttl


class MemoryAuditStore(DecisionAuditStoreProtocol):
    """Store de auditoria em memória — apenas para dev/test."""

    def __init__(self, max_records: int = 10000) -> None:
        self._records: list[dict[str, Any]] = []
        self._max_records = max_records

    def append(self, record: dict[str, Any]) -> None:
        """Append de registro de auditoria."""
        self._records.append(record)
        # Limita tamanho para evitar memory leak em dev
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

    def get_records(self) -> list[dict[str, Any]]:
        """Retorna todos os registros (apenas para testes)."""
        return list(self._records)
