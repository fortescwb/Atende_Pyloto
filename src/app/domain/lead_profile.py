"""Legacy alias para ContactCard (remover apos 1 release)."""

from __future__ import annotations

from app.domain.contact_card import ContactCard, ContactCardPatch

# TODO: remover alias apos migracao completa para ContactCard.
LeadProfile = ContactCard

__all__ = ["ContactCard", "ContactCardPatch", "LeadProfile"]
