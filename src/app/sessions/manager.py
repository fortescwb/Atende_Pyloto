"""Gerenciador de sessões para atendimento."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import TYPE_CHECKING

from app.domain.contact_card import ContactCard
from app.sessions.manager_persistence import (
    persist_lead_to_firestore,
    persist_message_to_firestore,
)
from app.sessions.manager_recovery import create_new_session, recover_contact_and_history
from app.sessions.session_entity import Session

if TYPE_CHECKING:
    from app.protocols.conversation_store import ConversationStoreProtocol
    from app.protocols.session_store import AsyncSessionStoreProtocol
    from app.sessions.history import HistoryEntry, HistoryRole

logger = logging.getLogger(__name__)
DEFAULT_SESSION_TTL_SECONDS = 7200


class SessionManager:
    __slots__ = ("_conversation_store", "_store", "_ttl_seconds")

    def __init__(
        self,
        store: AsyncSessionStoreProtocol,
        ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
        conversation_store: ConversationStoreProtocol | None = None,
    ) -> None:
        self._store = store
        self._ttl_seconds = ttl_seconds
        self._conversation_store = conversation_store

    @staticmethod
    def _hash_sender(sender_id: str) -> str:
        return hashlib.sha256(sender_id.encode()).hexdigest()[:16]

    def _generate_session_id(self, sender_hash: str) -> str:
        return f"sess_{sender_hash}"

    async def resolve_or_create(
        self,
        sender_id: str,
        tenant_id: str = "",
        vertente: str = "geral",
        whatsapp_name: str | None = None,
    ) -> Session:
        sender_hash = self._hash_sender(sender_id)
        session_id = self._generate_session_id(sender_hash)
        existing = await self._store.load_async(session_id)
        if existing is not None:
            session = existing if isinstance(existing, Session) else Session.from_dict(existing)
            if not session.is_expired and not session.is_terminal:
                logger.debug("session_resolved", extra={"session_id": session.session_id})
                return session
        return await self._create_with_recovery(
            sender_hash=sender_hash,
            session_id=session_id,
            tenant_id=tenant_id,
            vertente=vertente,
            wa_id=sender_id,
            whatsapp_name=whatsapp_name,
        )

    async def _create_with_recovery(
        self,
        *,
        sender_hash: str,
        session_id: str,
        tenant_id: str,
        vertente: str,
        wa_id: str,
        whatsapp_name: str | None,
    ) -> Session:
        contact_card: ContactCard | None = None
        recovered_history: list[HistoryEntry] = []
        if self._conversation_store is not None:
            try:
                contact_card, recovered_history = await recover_contact_and_history(
                    conversation_store=self._conversation_store,
                    sender_hash=sender_hash,
                    tenant_id=tenant_id,
                    wa_id=wa_id,
                    whatsapp_name=whatsapp_name,
                )
                if contact_card and contact_card.full_name:
                    logger.info(
                        "session_history_recovered",
                        extra={
                            "sender_hash": sender_hash[:8],
                            "contact_name": True,
                            "messages_recovered": len(recovered_history),
                        },
                    )
            except Exception as exc:
                logger.warning(
                    "session_recovery_failed",
                    extra={"error": str(exc), "sender_hash": sender_hash[:8]},
                )
        if contact_card is None and whatsapp_name:
            contact_card = ContactCard(wa_id=wa_id, phone=wa_id, whatsapp_name=whatsapp_name)
        return await create_new_session(
            store=self._store,
            ttl_seconds=self._ttl_seconds,
            sender_hash=sender_hash,
            session_id=session_id,
            tenant_id=tenant_id,
            vertente=vertente,
            contact_card=contact_card,
            recovered_history=recovered_history,
        )

    async def add_message(
        self,
        session: Session,
        content: str,
        role: HistoryRole,
        *,
        detected_intent: str | None = None,
        channel: str = "whatsapp",
        message_id: str | None = None,
    ) -> None:
        session.add_to_history(content, role, detected_intent)
        await self.save(session)
        if self._conversation_store is not None:
            asyncio.create_task(  # noqa: RUF006
                persist_message_to_firestore(
                    conversation_store=self._conversation_store,
                    session=session,
                    content=content,
                    role=role,
                    detected_intent=detected_intent,
                    channel=channel,
                    message_id=message_id,
                )
            )

    async def update_contact_card(
        self,
        session: Session,
        *,
        full_name: str | None = None,
        email: str | None = None,
        primary_interest: str | None = None,
    ) -> None:
        if session.contact_card is None:
            return
        if full_name:
            session.contact_card.full_name = full_name
        if email:
            session.contact_card.email = email
        if primary_interest:
            session.contact_card.primary_interest = primary_interest
        await self.save(session)
        if self._conversation_store is not None:
            asyncio.create_task(  # noqa: RUF006
                persist_lead_to_firestore(
                    conversation_store=self._conversation_store,
                    session=session,
                )
            )

    async def save(self, session: Session) -> None:
        await self._store.save_async(session.to_dict(), self._ttl_seconds)
        logger.debug("session_saved", extra={"session_id": session.session_id})

    async def close(self, session: Session, reason: str = "normal") -> None:
        await self._store.delete_async(session.session_id)
        logger.info("session_closed", extra={"session_id": session.session_id, "reason": reason})
