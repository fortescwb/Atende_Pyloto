"""Helpers de dual-write do SessionManager."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.protocols.conversation_store import ConversationMessage, LeadData
from app.sessions.history import HistoryRole

if TYPE_CHECKING:
    from app.protocols.conversation_store import ConversationStoreProtocol
    from app.sessions.session_entity import Session

logger = logging.getLogger(__name__)


async def persist_message_to_firestore(
    *,
    conversation_store: ConversationStoreProtocol,
    session: Session,
    content: str,
    role: HistoryRole,
    detected_intent: str | None,
    channel: str,
    message_id: str | None,
) -> None:
    """Persiste mensagem no Firestore sem propagar falhas."""
    try:
        msg_id = message_id or f"{datetime.now(UTC).timestamp()}_{uuid.uuid4().hex[:8]}"
        message = ConversationMessage(
            message_id=msg_id,
            role="assistant" if role == HistoryRole.ASSISTANT else "user",
            content=content,
            timestamp=datetime.now(UTC),
            channel=channel,
            detected_intent=detected_intent or "",
        )
        await conversation_store.append_message(
            phone_hash=session.sender_id,
            message=message,
            tenant_id=session.context.tenant_id or "default",
        )
        logger.debug(
            "message_persisted_firestore",
            extra={
                "session_id": session.session_id,
                "message_id": msg_id,
                "role": role.value,
            },
        )
    except Exception as exc:
        logger.warning(
            "firestore_persist_failed",
            extra={"error": str(exc), "session_id": session.session_id},
        )


async def persist_lead_to_firestore(
    *,
    conversation_store: ConversationStoreProtocol,
    session: Session,
) -> None:
    """Persiste lead no Firestore sem propagar falhas."""
    try:
        contact = session.contact_card
        if contact is None:
            return
        lead = LeadData(
            phone_hash=session.sender_id,
            name=contact.full_name or contact.whatsapp_name or "",
            email=contact.email or "",
            primary_intent=contact.primary_interest or "",
            tenant_id=session.context.tenant_id or "default",
            last_contact=datetime.now(UTC),
        )
        await conversation_store.upsert_lead(lead)
        logger.debug("lead_persisted_firestore", extra={"session_id": session.session_id})
    except Exception as exc:
        logger.warning(
            "firestore_lead_persist_failed",
            extra={"error": str(exc), "session_id": session.session_id},
        )
