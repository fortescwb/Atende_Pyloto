"""Backend síncrono para persistência de conversas no Firestore."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.protocols.conversation_store import (
    ConversationMessage,
    ConversationStoreError,
    LeadData,
)

if TYPE_CHECKING:
    from google.cloud.firestore import Client as FirestoreClient

logger = logging.getLogger(__name__)

CONVERSATIONS_COLLECTION = "conversations"
LEADS_COLLECTION = "leads"


class FirestoreConversationBackend:
    """Implementação síncrona de operações de conversa no Firestore."""

    def __init__(self, firestore_client: FirestoreClient) -> None:
        self._db = firestore_client

    @staticmethod
    def conversation_key(phone_hash: str, tenant_id: str) -> str:
        return f"{tenant_id}_{phone_hash}"

    def append_message(
        self,
        phone_hash: str,
        message: ConversationMessage,
        tenant_id: str,
    ) -> None:
        conv_key = self.conversation_key(phone_hash, tenant_id)
        doc_data = {
            "message_id": message.message_id,
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "channel": message.channel,
            "detected_intent": message.detected_intent,
            "metadata": message.metadata,
            "created_at": datetime.now(UTC),
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
        except Exception as exc:
            logger.error(
                "conversation_append_error",
                extra={"error": str(exc), "conv_key": conv_key},
            )
            raise ConversationStoreError(f"Erro ao persistir mensagem: {exc}") from exc

    def get_messages(
        self,
        phone_hash: str,
        limit: int,
        tenant_id: str,
    ) -> list[ConversationMessage]:
        conv_key = self.conversation_key(phone_hash, tenant_id)
        try:
            docs = (
                self._db.collection(CONVERSATIONS_COLLECTION)
                .document(conv_key)
                .collection("messages")
                .order_by("timestamp")
                .limit(limit)
                .stream()
            )
            messages: list[ConversationMessage] = []
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
        except Exception as exc:
            logger.error(
                "conversation_get_error",
                extra={"error": str(exc), "conv_key": conv_key},
            )
            return []

    def upsert_lead(self, lead: LeadData) -> None:
        lead_key = self.conversation_key(lead.phone_hash, lead.tenant_id)
        doc_data = {
            "phone_hash": lead.phone_hash,
            "name": lead.name,
            "email": lead.email,
            "first_contact": lead.first_contact.isoformat() if lead.first_contact else None,
            "last_contact": lead.last_contact.isoformat() if lead.last_contact else None,
            "primary_intent": lead.primary_intent,
            "total_messages": lead.total_messages,
            "tenant_id": lead.tenant_id,
            "channel": lead.channel,
            "metadata": lead.metadata,
            "updated_at": datetime.now(UTC),
        }
        try:
            self._db.collection(LEADS_COLLECTION).document(lead_key).set(doc_data, merge=True)
            logger.debug("lead_upserted", extra={"lead_key": lead_key})
        except Exception as exc:
            logger.error(
                "lead_upsert_error",
                extra={"error": str(exc), "lead_key": lead_key},
            )
            raise ConversationStoreError(f"Erro ao persistir lead: {exc}") from exc

    def get_lead(self, phone_hash: str, tenant_id: str) -> LeadData | None:
        lead_key = self.conversation_key(phone_hash, tenant_id)
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
        except Exception as exc:
            logger.error(
                "lead_get_error",
                extra={"error": str(exc), "lead_key": lead_key},
            )
            return None
