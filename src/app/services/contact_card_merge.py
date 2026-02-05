"""Merge deterministico de ContactCard com patch."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai.models.contact_card_extraction import ContactCardPatch
    from app.domain.contact_card import ContactCard


def apply_contact_card_patch(contact_card: ContactCard, patch: ContactCardPatch) -> bool:
    """Aplica patch no ContactCard respeitando regras de merge.

    Regras:
    - Preencher somente campos vazios.
    - urgency pode atualizar mesmo se ja preenchido.
    - flags booleanas so evoluem para True.
    """
    updated = False
    data = patch.model_dump(exclude_none=True)

    for field, value in data.items():
        if field == "urgency":
            if value and value != contact_card.urgency:
                contact_card.urgency = value
                updated = True
            continue

        if field in {"requested_human", "showed_objection"}:
            if value is True and getattr(contact_card, field) is False:
                setattr(contact_card, field, True)
                updated = True
            continue

        if field == "secondary_interests":
            if value and not contact_card.secondary_interests:
                contact_card.secondary_interests = list(value)
                updated = True
            continue

        current = getattr(contact_card, field, None)
        if _is_empty_value(current):
            setattr(contact_card, field, value)
            updated = True

    if updated:
        contact_card.calculate_qualification_score()

    return updated


def _is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, list):
        return len(value) == 0
    if isinstance(value, dict):
        return len(value) == 0
    return False
