"""Legacy alias para ContactCardStoreProtocol (remover apos 1 release)."""

from __future__ import annotations

from app.protocols.contact_card_store import ContactCardStoreProtocol

LeadProfileStoreProtocol = ContactCardStoreProtocol

__all__ = ["ContactCardStoreProtocol", "LeadProfileStoreProtocol"]
