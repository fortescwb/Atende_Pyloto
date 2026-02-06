"""Prompts ativos na arquitetura Otto (agente único + utilitários)."""

from ai.prompts.contact_card_extractor_prompt import (
    CONTACT_CARD_EXTRACTOR_SYSTEM,
    format_contact_card_extractor_prompt,
)
from ai.prompts.otto_prompt import OTTO_SYSTEM_PROMPT, build_full_prompt, format_otto_prompt

__all__ = [
    "CONTACT_CARD_EXTRACTOR_SYSTEM",
    "OTTO_SYSTEM_PROMPT",
    "build_full_prompt",
    "format_contact_card_extractor_prompt",
    "format_otto_prompt",
]
