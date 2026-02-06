"""Prompts do ContactCardExtractor (agente utilitário).

Regra: nenhum conteúdo de prompt hardcoded em `.py` (vem de YAML).
"""

from __future__ import annotations

from ai.config.prompt_assets_loader import load_prompt_template, load_system_prompt

CONTACT_CARD_EXTRACTOR_SYSTEM = load_system_prompt("contact_card_extractor_system.yaml")
_CONTACT_CARD_EXTRACTOR_USER_TEMPLATE = load_prompt_template(
    "contact_card_extractor_user_template.yaml"
)


def format_contact_card_extractor_prompt(
    *,
    user_message: str,
    assistant_last_message: str | None = None,
) -> str:
    """Formata prompt do ContactCardExtractor (msg atual + ultima do assistente)."""
    return _CONTACT_CARD_EXTRACTOR_USER_TEMPLATE.format(
        user_message=(user_message or "")[:600],
        assistant_last_message=(assistant_last_message or "")[:400],
    )
