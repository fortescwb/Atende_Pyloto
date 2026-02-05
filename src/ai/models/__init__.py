"""Modelos/DTOs ativos para IA (arquitetura Otto)."""

from ai.models.contact_card_extraction import (
    ContactCardExtractionRequest,
    ContactCardExtractionResult,
    ContactCardPatch,
)
from ai.models.otto import OttoDecision, OttoRequest
from ai.models.validation import ValidationResult

__all__ = [
    "ContactCardExtractionRequest",
    "ContactCardExtractionResult",
    "ContactCardPatch",
    "OttoDecision",
    "OttoRequest",
    "ValidationResult",
]
