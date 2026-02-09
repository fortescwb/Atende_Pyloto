"""Merge deterministico de ContactCard com patch."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai.models.contact_card_extraction import ContactCardPatch
    from app.domain.contact_card import ContactCard

_DIRECT_UPDATE_FIELDS = {"primary_interest", "has_crm", "needs_data_migration", "meeting_mode"}
_INT_FIELDS = {"message_volume_per_day", "attendants_count", "specialists_count", "users_count"}
_TRUE_ONLY_FLAGS = {"requested_human", "showed_objection"}
_LIST_FIELD_LIMITS = {
    "secondary_interests": 3,
    "current_tools": 8,
    "modules_needed": 12,
    "desired_features": 12,
    "integrations_needed": 12,
    "legacy_systems": 12,
}


def apply_contact_card_patch(contact_card: ContactCard, patch: ContactCardPatch) -> bool:
    """Aplica patch no ContactCard respeitando regras de merge.

    Regras:
    - Preencher somente campos vazios.
    - urgency pode atualizar mesmo se ja preenchido.
    - flags booleanas so evoluem para True.
    """
    updated = False
    for field, value in patch.model_dump(exclude_none=True).items():
        if _apply_specialized_field(contact_card, field, value):
            updated = True
            continue
        current = getattr(contact_card, field, None)
        if _is_empty_value(current):
            setattr(contact_card, field, value)
            updated = True

    if updated:
        contact_card.calculate_qualification_score()

    return updated


def _apply_specialized_field(contact_card: ContactCard, field: str, value: Any) -> bool:
    if field == "urgency":
        return _set_if_changed(contact_card, field, value) if value else False
    if field in _DIRECT_UPDATE_FIELDS:
        return _set_if_changed(contact_card, field, value)
    if field in _INT_FIELDS:
        return _set_if_changed(contact_card, field, int(value))
    if field in _TRUE_ONLY_FLAGS:
        return _promote_flag_to_true(contact_card, field, value)
    if field in _LIST_FIELD_LIMITS:
        return _merge_list_field(contact_card, field, value, _LIST_FIELD_LIMITS[field])
    if field == "meeting_preferred_datetime_text":
        return _set_if_changed(contact_card, field, str(value)) if value else False
    return False


def _set_if_changed(contact_card: ContactCard, field: str, value: Any) -> bool:
    if value is None or value == getattr(contact_card, field, None):
        return False
    setattr(contact_card, field, value)
    return True


def _promote_flag_to_true(contact_card: ContactCard, field: str, value: Any) -> bool:
    if value is True and getattr(contact_card, field) is False:
        setattr(contact_card, field, True)
        return True
    return False


def _merge_list_field(
    contact_card: ContactCard,
    field: str,
    value: Any,
    limit: int,
) -> bool:
    if not value:
        return False
    existing = list(getattr(contact_card, field, []) or [])
    merged = _merge_unique(existing, list(value), limit)
    if merged == existing:
        return False
    setattr(contact_card, field, merged)
    return True


def _merge_unique(existing: list[str], incoming: list[Any], limit: int) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in existing + incoming:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        merged.append(text)
        if len(merged) >= limit:
            break
    return merged


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
