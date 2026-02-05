"""Implementacoes de store para ContactCard.

Memory: desenvolvimento/testes.
Redis: opcional para staging/produção.
"""

from __future__ import annotations

import logging
from typing import Any

from app.domain.contact_card import ContactCard

logger = logging.getLogger(__name__)

CONTACT_CARD_PREFIX = "contact_card:"
CONTACT_CARD_INDEX = "contact_cards:index"


class MemoryContactCardStore:
    """Store em memoria para desenvolvimento/testes."""

    def __init__(self) -> None:
        self._cards: dict[str, ContactCard] = {}

    async def get(self, wa_id: str) -> ContactCard | None:
        return self._cards.get(wa_id)

    async def get_or_create(self, wa_id: str, whatsapp_name: str) -> ContactCard:
        card = self._cards.get(wa_id)
        if card is None:
            card = ContactCard(wa_id=wa_id, phone=wa_id, whatsapp_name=whatsapp_name)
            self._cards[wa_id] = card
            logger.info("contact_card_created", extra={"backend": "memory"})
        return card

    async def upsert(self, contact_card: ContactCard) -> None:
        self._cards[contact_card.wa_id] = contact_card


class RedisContactCardStore:
    """Store Redis para ContactCard (opcional)."""

    def __init__(
        self,
        redis_client: Any,
        async_client: Any | None = None,
    ) -> None:
        self._redis = redis_client
        self._async_redis = async_client

    def _key(self, wa_id: str) -> str:
        return f"{CONTACT_CARD_PREFIX}{wa_id}"

    async def get(self, wa_id: str) -> ContactCard | None:
        if self._async_redis:
            data = await self._async_redis.get(self._key(wa_id))
        else:
            data = self._redis.get(self._key(wa_id))

        if not data:
            return None

        try:
            data_str = data if isinstance(data, str) else data.decode()
            return ContactCard.model_validate_json(data_str)
        except Exception as exc:
            logger.warning(
                "contact_card_parse_error",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            return None

    async def get_or_create(self, wa_id: str, whatsapp_name: str) -> ContactCard:
        card = await self.get(wa_id)
        if card is None:
            card = ContactCard(wa_id=wa_id, phone=wa_id, whatsapp_name=whatsapp_name)
            await self.upsert(card)
        return card

    async def upsert(self, contact_card: ContactCard) -> None:
        payload = contact_card.model_dump_json(exclude_none=True)
        key = self._key(contact_card.wa_id)
        if self._async_redis:
            await self._async_redis.set(key, payload)
            await self._async_redis.sadd(CONTACT_CARD_INDEX, contact_card.wa_id)
        else:
            self._redis.set(key, payload)
            self._redis.sadd(CONTACT_CARD_INDEX, contact_card.wa_id)
