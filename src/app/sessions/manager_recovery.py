"""Helpers de recuperação e criação inicial de sessão."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.domain.contact_card import ContactCard
from app.sessions.history import HistoryEntry, HistoryRole
from app.sessions.session_context import SessionContext
from app.sessions.session_entity import Session
from fsm.states import DEFAULT_INITIAL_STATE

if TYPE_CHECKING:
    from app.protocols.conversation_store import ConversationStoreProtocol
    from app.protocols.session_store import AsyncSessionStoreProtocol

DEFAULT_HISTORY_RECOVERY_LIMIT = 20
logger = logging.getLogger(__name__)

_ALLOWED_PRIMARY_INTERESTS = {
    "saas",
    "sob_medida",
    "gestao_perfis_trafego",
    "intermediacao_entregas",
    "gestao_perfis",
    "trafego_pago",
    "automacao_atendimento",
    "intermediacao",
    None,
}


def normalize_primary_interest(primary_interest: str | None) -> str | None:
    """Normaliza interesse principal recuperado do histórico."""
    if primary_interest in _ALLOWED_PRIMARY_INTERESTS:
        return primary_interest
    return None


def build_contact_card_from_lead(
    *,
    lead_data: object,
    wa_id: str,
    whatsapp_name: str | None,
) -> ContactCard | None:
    """Converte LeadData em ContactCard."""
    if lead_data is None or not whatsapp_name:
        return None
    return ContactCard(
        wa_id=wa_id,
        phone=wa_id,
        whatsapp_name=whatsapp_name,
        full_name=getattr(lead_data, "name", "") or None,
        email=getattr(lead_data, "email", "") or None,
        primary_interest=normalize_primary_interest(
            getattr(lead_data, "primary_intent", None) or None
        ),
        total_messages=getattr(lead_data, "total_messages", 0) or 0,
        last_updated_at=datetime.now(UTC),
    )


def build_history_entries(messages: list[object]) -> list[HistoryEntry]:
    """Converte mensagens persistidas para HistoryEntry."""
    history: list[HistoryEntry] = []
    for msg in messages:
        role = (
            HistoryRole.ASSISTANT
            if getattr(msg, "role", "user") == "assistant"
            else HistoryRole.USER
        )
        history.append(
            HistoryEntry(
                role=role,
                content=getattr(msg, "content", ""),
                timestamp=getattr(msg, "timestamp", datetime.now(UTC)),
                detected_intent=getattr(msg, "detected_intent", "") or None,
            )
        )
    return history


async def recover_contact_and_history(
    *,
    conversation_store: ConversationStoreProtocol,
    sender_hash: str,
    tenant_id: str,
    wa_id: str,
    whatsapp_name: str | None,
) -> tuple[ContactCard | None, list[HistoryEntry]]:
    """Recupera contato e histórico do Firestore em paralelo."""
    lead_task = asyncio.create_task(
        conversation_store.get_lead(sender_hash, tenant_id=tenant_id)
    )
    messages_task = asyncio.create_task(
        conversation_store.get_messages(
            sender_hash,
            limit=DEFAULT_HISTORY_RECOVERY_LIMIT,
            tenant_id=tenant_id,
        )
    )

    lead_data, messages = await asyncio.gather(lead_task, messages_task)
    return (
        build_contact_card_from_lead(
            lead_data=lead_data,
            wa_id=wa_id,
            whatsapp_name=whatsapp_name,
        ),
        build_history_entries(list(messages)),
    )


async def create_new_session(
    *,
    store: AsyncSessionStoreProtocol,
    ttl_seconds: int,
    sender_hash: str,
    session_id: str,
    tenant_id: str,
    vertente: str,
    contact_card: ContactCard | None,
    recovered_history: list[HistoryEntry] | None,
) -> Session:
    """Cria e persiste sessão inicial com TTL configurado."""
    now = datetime.now(UTC)
    session = Session(
        session_id=session_id,
        sender_id=sender_hash,
        current_state=DEFAULT_INITIAL_STATE,
        context=SessionContext(tenant_id=tenant_id, vertente=vertente),
        history=recovered_history or [],
        contact_card=contact_card,
        turn_count=0,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    await store.save_async(session.to_dict(), ttl_seconds)
    logger.info(
        "session_created",
        extra={
            "session_id": session_id,
            "recovered_contact": bool(contact_card and contact_card.full_name),
            "recovered_history_count": len(recovered_history or []),
        },
    )
    return session
