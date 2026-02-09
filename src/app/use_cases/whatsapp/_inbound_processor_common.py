"""Tipos e helpers compartilhados do processamento inbound."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class _FallbackDecision:
    response_text: str
    message_type: str = "text"


def _extract_contact_card_signals(contact_card: Any) -> dict[str, str]:
    if contact_card is None:
        return {}
    signals: dict[str, str] = {}
    for key in ("company_size", "budget_indication", "specific_need", "company", "role"):
        value = getattr(contact_card, key, None)
        if isinstance(value, str) and value.strip():
            signals[key] = value.strip()
    return signals
