"""Protocolo para persistencia de ContactCard."""

from __future__ import annotations

from typing import Protocol

from app.domain.contact_card import ContactCard


class ContactCardStoreProtocol(Protocol):
    """Contrato para store de ContactCard."""

    async def get(self, wa_id: str) -> ContactCard | None:
        """Busca ContactCard por wa_id."""
        ...

    async def get_or_create(self, wa_id: str, whatsapp_name: str) -> ContactCard:
        """Busca ContactCard ou cria um novo se nao existir."""
        ...

    async def upsert(self, contact_card: ContactCard) -> None:
        """Cria ou atualiza ContactCard."""
        ...
