"""Gerenciador de sessões para atendimento.

Resolve, cria e atualiza sessões de atendimento.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.sessions.models import Session, SessionContext
from fsm.states import DEFAULT_INITIAL_STATE

if TYPE_CHECKING:
    from app.protocols.session_store import AsyncSessionStoreProtocol

logger = logging.getLogger(__name__)

DEFAULT_SESSION_TTL_SECONDS = 7200


class SessionManager:
    """Gerenciador de sessões de atendimento."""

    __slots__ = ("_store", "_ttl_seconds")

    def __init__(
        self,
        store: AsyncSessionStoreProtocol,
        ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
    ) -> None:
        """Inicializa gerenciador."""
        self._store = store
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def _hash_sender(sender_id: str) -> str:
        """Gera hash do sender_id para uso como chave."""
        return hashlib.sha256(sender_id.encode()).hexdigest()[:16]

    def _generate_session_id(self, sender_hash: str) -> str:
        """Gera ID único para sessão."""
        return f"sess_{sender_hash}_{uuid.uuid4().hex[:8]}"

    async def resolve_or_create(
        self,
        sender_id: str,
        tenant_id: str = "",
        vertente: str = "geral",
    ) -> Session:
        """Resolve sessão existente ou cria nova."""
        sender_hash = self._hash_sender(sender_id)
        lookup_key = f"session:{sender_hash}"

        existing = await self._store.load_async(lookup_key)
        if existing is not None:
            session = Session.from_dict(existing)
            if not session.is_expired and not session.is_terminal:
                logger.debug("session_resolved", extra={"session_id": session.session_id})
                return session

        return await self._create_new(sender_hash, lookup_key, tenant_id, vertente)

    async def _create_new(
        self,
        sender_hash: str,
        lookup_key: str,
        tenant_id: str,
        vertente: str,
    ) -> Session:
        """Cria nova sessão."""
        session_id = self._generate_session_id(sender_hash)
        now = datetime.now(UTC)

        session = Session(
            session_id=session_id,
            sender_id=sender_hash,
            current_state=DEFAULT_INITIAL_STATE,
            context=SessionContext(tenant_id=tenant_id, vertente=vertente),
            history=[],
            turn_count=0,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(seconds=self._ttl_seconds),
        )

        await self._store.save_async(session.to_dict(), self._ttl_seconds)
        logger.info("session_created", extra={"session_id": session_id})
        return session

    async def save(self, session: Session) -> None:
        """Persiste sessão atualizada."""
        await self._store.save_async(session.to_dict(), self._ttl_seconds)
        logger.debug("session_saved", extra={"session_id": session.session_id})

    async def close(self, session: Session, reason: str = "normal") -> None:
        """Encerra sessão explicitamente."""
        lookup_key = f"session:{session.sender_id}"
        await self._store.delete_async(lookup_key)
        logger.info("session_closed", extra={"session_id": session.session_id, "reason": reason})
