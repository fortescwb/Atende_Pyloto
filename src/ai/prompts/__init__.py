"""Prompts ativos na arquitetura Otto (agente único + utilitários)."""

from ai.prompts.contact_card_extractor_prompt import (
    CONTACT_CARD_EXTRACTOR_SYSTEM,
    format_contact_card_extractor_prompt,
)
from ai.prompts.otto_prompt import OTTO_SYSTEM_PROMPT, format_otto_prompt
from ai.prompts.system_role import SYSTEM_ROLE

__all__ = [
    "CONTACT_CARD_EXTRACTOR_SYSTEM",
    "OTTO_SYSTEM_PROMPT",
    "SYSTEM_ROLE",
    "format_contact_card_extractor_prompt",
    "format_otto_prompt",
]
