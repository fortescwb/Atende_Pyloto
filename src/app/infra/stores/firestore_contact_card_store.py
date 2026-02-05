"""Firestore ContactCard Store."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.domain.contact_card import ContactCard
from app.protocols.contact_card_store import ContactCardStoreProtocol

if TYPE_CHECKING:
    from google.cloud.firestore import Client as FirestoreClient

logger = logging.getLogger(__name__)

CONTACT_CARDS_COLLECTION = "lead_contacts"


class FirestoreContactCardStore(ContactCardStoreProtocol):
    """Store de ContactCard usando Firestore."""

    def __init__(self, firestore_client: FirestoreClient) -> None:
        self._db = firestore_client

    async def get(self, wa_id: str) -> ContactCard | None:
        return await asyncio.to_thread(self._get_sync, wa_id)

    def _get_sync(self, wa_id: str) -> ContactCard | None:
        try:
            doc = self._db.collection(CONTACT_CARDS_COLLECTION).document(wa_id).get()
            if not doc.exists:
                return None
            data = doc.to_dict() or {}
            return ContactCard.from_firestore_dict(data)
        except Exception as exc:
            logger.error(
                "contact_card_get_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            return None

    async def get_or_create(self, wa_id: str, whatsapp_name: str) -> ContactCard:
        existing = await self.get(wa_id)
        if existing is not None:
            return existing

        contact_card = ContactCard(
            wa_id=wa_id,
            phone=wa_id,
            whatsapp_name=whatsapp_name,
        )
        await self.upsert(contact_card)
        return contact_card

    async def upsert(self, contact_card: ContactCard) -> None:
        await asyncio.to_thread(self._upsert_sync, contact_card)

    def _upsert_sync(self, contact_card: ContactCard) -> None:
        try:
            data = contact_card.to_firestore_dict()
            self._db.collection(CONTACT_CARDS_COLLECTION).document(contact_card.wa_id).set(
                data, merge=True
            )
            logger.debug("contact_card_upserted")
        except Exception as exc:
            logger.error(
                "contact_card_upsert_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
