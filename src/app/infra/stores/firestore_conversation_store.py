"""Store assíncrona de conversas usando backend Firestore síncrono."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from app.infra.stores.firestore_conversation_backend import FirestoreConversationBackend
from app.protocols.conversation_store import (
    ConversationMessage,
    ConversationStoreProtocol,
    LeadData,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from google.cloud.firestore import Client as FirestoreClient

CONVERSATIONS_COLLECTION = "conversations"
LEADS_COLLECTION = "leads"


class FirestoreConversationStore(ConversationStoreProtocol):
    """Adapter async para persistência de conversas no Firestore."""

    def __init__(self, firestore_client: FirestoreClient) -> None:
        self._backend = FirestoreConversationBackend(firestore_client)

    def _get_conversation_key(self, phone_hash: str, tenant_id: str) -> str:
        """Mantém compatibilidade com chave composta tenant+telefone."""
        return self._backend.conversation_key(phone_hash, tenant_id)

    async def append_message(
        self,
        phone_hash: str,
        message: ConversationMessage,
        *,
        tenant_id: str = "default",
    ) -> None:
        await asyncio.to_thread(self._backend.append_message, phone_hash, message, tenant_id)

    async def get_messages(
        self,
        phone_hash: str,
        *,
        limit: int = 20,
        tenant_id: str = "default",
    ) -> Sequence[ConversationMessage]:
        return await asyncio.to_thread(
            self._backend.get_messages,
            phone_hash,
            limit,
            tenant_id,
        )

    async def upsert_lead(self, lead: LeadData) -> None:
        await asyncio.to_thread(self._backend.upsert_lead, lead)

    async def get_lead(
        self,
        phone_hash: str,
        *,
        tenant_id: str = "default",
    ) -> LeadData | None:
        return await asyncio.to_thread(self._backend.get_lead, phone_hash, tenant_id)
