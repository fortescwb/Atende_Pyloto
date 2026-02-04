"""Firestore Conversation Store — persistência permanente de conversas.

Store para persistir mensagens e dados de leads no Firestore.
Implementa dual-write pattern para recuperação de contexto.

Referência: TODO_llm.md § 7 — Persistência de Conversas (Firestore)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.protocols.conversation_store import (
    ConversationMessage,
    ConversationStoreError,
    ConversationStoreProtocol,
    LeadData,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from google.cloud.firestore import Client as FirestoreClient

logger = logging.getLogger(__name__)

# Collections Firestore
CONVERSATIONS_COLLECTION = "conversations"
LEADS_COLLECTION = "leads"


class FirestoreConversationStore(ConversationStoreProtocol):
    """Store de conversas usando Firestore.

    Estrutura no Firestore:
        conversations/{tenant_id}_{phone_hash}/messages/{message_id}
        leads/{tenant_id}_{phone_hash}

    Características:
        - Append-only para mensagens
        - Upsert para leads
        - Particionado por tenant
        - TTL via Firestore TTL policies (configurar no console)

    Args:
        firestore_client: Cliente Firestore
    """

    def __init__(
        self,
        firestore_client: FirestoreClient,
    ) -> None:
        self._db = firestore_client

    def _get_conversation_key(self, phone_hash: str, tenant_id: str) -> str:
        """Gera chave única para conversa (tenant + phone_hash)."""
        return f"{tenant_id}_{phone_hash}"

    async def append_message(
        self,
        phone_hash: str,
        message: ConversationMessage,
        *,
        tenant_id: str = "default",
    ) -> None:
        """Persiste uma mensagem de conversa.

        Usa asyncio.to_thread pois Firestore SDK não tem async nativo.
        """
        await asyncio.to_thread(
            self._append_message_sync,
            phone_hash,
            message,
            tenant_id,
        )

    def _append_message_sync(
        self,
        phone_hash: str,
        message: ConversationMessage,
        tenant_id: str,
    ) -> None:
        """Implementação síncrona de append_message."""
        conv_key = self._get_conversation_key(phone_hash, tenant_id)

        doc_data = {
            "message_id": message.message_id,
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "channel": message.channel,
            "detected_intent": message.detected_intent,
            "metadata": message.metadata,
            "created_at": datetime.now(UTC),  # Para TTL
        }

        try:
            (
                self._db.collection(CONVERSATIONS_COLLECTION)
                .document(conv_key)
                .collection("messages")
                .document(message.message_id)
                .set(doc_data)
            )
            logger.debug(
                "conversation_message_appended",
                extra={
                    "conv_key": conv_key,
                    "message_id": message.message_id,
                    "role": message.role,
                },
            )
        except Exception as e:
            logger.error(
                "conversation_append_error",
                extra={"error": str(e), "conv_key": conv_key},
            )
            raise ConversationStoreError(f"Erro ao persistir mensagem: {e}") from e

    async def get_messages(
        self,
        phone_hash: str,
        *,
        limit: int = 20,
        tenant_id: str = "default",
    ) -> Sequence[ConversationMessage]:
        """Recupera últimas mensagens de um lead."""
        return await asyncio.to_thread(
            self._get_messages_sync,
            phone_hash,
            limit,
            tenant_id,
        )

    def _get_messages_sync(
        self,
        phone_hash: str,
        limit: int,
        tenant_id: str,
    ) -> list[ConversationMessage]:
        """Implementação síncrona de get_messages."""
        conv_key = self._get_conversation_key(phone_hash, tenant_id)

        try:
            docs = (
                self._db.collection(CONVERSATIONS_COLLECTION)
                .document(conv_key)
                .collection("messages")
                .order_by("timestamp")
                .limit(limit)
                .stream()
            )

            messages = []
            for doc in docs:
                data = doc.to_dict()
                messages.append(
                    ConversationMessage(
                        message_id=data.get("message_id", doc.id),
                        role=data.get("role", "user"),
                        content=data.get("content", ""),
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        channel=data.get("channel", "whatsapp"),
                        detected_intent=data.get("detected_intent", ""),
                        metadata=data.get("metadata", {}),
                    )
                )

            logger.debug(
                "conversation_messages_retrieved",
                extra={"conv_key": conv_key, "count": len(messages)},
            )
            return messages

        except Exception as e:
            logger.error(
                "conversation_get_error",
                extra={"error": str(e), "conv_key": conv_key},
            )
            return []

    async def upsert_lead(
        self,
        lead: LeadData,
    ) -> None:
        """Cria ou atualiza dados do lead."""
        await asyncio.to_thread(self._upsert_lead_sync, lead)

    def _upsert_lead_sync(self, lead: LeadData) -> None:
        """Implementação síncrona de upsert_lead."""
        lead_key = self._get_conversation_key(lead.phone_hash, lead.tenant_id)

        doc_data = {
            "phone_hash": lead.phone_hash,
            "name": lead.name,
            "email": lead.email,
            "first_contact": (
                lead.first_contact.isoformat() if lead.first_contact else None
            ),
            "last_contact": (
                lead.last_contact.isoformat() if lead.last_contact else None
            ),
            "primary_intent": lead.primary_intent,
            "total_messages": lead.total_messages,
            "tenant_id": lead.tenant_id,
            "channel": lead.channel,
            "metadata": lead.metadata,
            "updated_at": datetime.now(UTC),
        }

        try:
            self._db.collection(LEADS_COLLECTION).document(lead_key).set(
                doc_data, merge=True
            )
            logger.debug(
                "lead_upserted",
                extra={"lead_key": lead_key},
            )
        except Exception as e:
            logger.error(
                "lead_upsert_error",
                extra={"error": str(e), "lead_key": lead_key},
            )
            raise ConversationStoreError(f"Erro ao persistir lead: {e}") from e

    async def get_lead(
        self,
        phone_hash: str,
        *,
        tenant_id: str = "default",
    ) -> LeadData | None:
        """Recupera dados de um lead."""
        return await asyncio.to_thread(
            self._get_lead_sync,
            phone_hash,
            tenant_id,
        )

    def _get_lead_sync(
        self,
        phone_hash: str,
        tenant_id: str,
    ) -> LeadData | None:
        """Implementação síncrona de get_lead."""
        lead_key = self._get_conversation_key(phone_hash, tenant_id)

        try:
            doc = self._db.collection(LEADS_COLLECTION).document(lead_key).get()

            if not doc.exists:
                return None

            data = doc.to_dict()
            return LeadData(
                phone_hash=data.get("phone_hash", phone_hash),
                name=data.get("name", ""),
                email=data.get("email", ""),
                first_contact=(
                    datetime.fromisoformat(data["first_contact"])
                    if data.get("first_contact")
                    else None
                ),
                last_contact=(
                    datetime.fromisoformat(data["last_contact"])
                    if data.get("last_contact")
                    else None
                ),
                primary_intent=data.get("primary_intent", ""),
                total_messages=data.get("total_messages", 0),
                tenant_id=data.get("tenant_id", tenant_id),
                channel=data.get("channel", "whatsapp"),
                metadata=data.get("metadata", {}),
            )

        except Exception as e:
            logger.error(
                "lead_get_error",
                extra={"error": str(e), "lead_key": lead_key},
            )
            return None
