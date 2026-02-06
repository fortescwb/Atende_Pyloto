"""Prompt do OttoAgent (agente principal).

Regras:
  - Nenhuma string de prompt vive em `.py`; tudo é carregado de YAML.
  - SYSTEM é composto por contextos sempre carregados (ver `context_builder.py`).
  - USER usa template YAML com placeholders determinísticos.
"""

from __future__ import annotations

from ai.config.prompt_assets_loader import load_prompt_template
from ai.prompts.context_builder import build_contexts

_OTTO_USER_TEMPLATE = load_prompt_template("otto_user_template.yaml")


def build_otto_system_prompt() -> str:
    """Monta o SYSTEM prompt padronizado do Otto."""
    return build_contexts().get("system_context", "")


OTTO_SYSTEM_PROMPT = build_otto_system_prompt()


def format_otto_prompt(
    *,
    user_message: str,
    session_state: str,
    valid_transitions: list[str],
    institutional_context: str,
    tenant_context: str,
    contact_card_summary: str,
    conversation_history: str,
) -> str:
    """Formata USER prompt do OttoAgent."""
    return _OTTO_USER_TEMPLATE.format(
        user_message=(user_message or "")[:800],
        session_state=session_state or "",
        valid_transitions=", ".join(valid_transitions) if valid_transitions else "Nenhuma",
        institutional_context=(institutional_context or "(vazio)")[:2000],
        tenant_context=(tenant_context or "(vazio)")[:1200],
        contact_card_summary=(contact_card_summary or "(vazio)")[:1200],
        conversation_history=(conversation_history or "(sem historico)")[:1200],
    )


def build_full_prompt(
    *,
    contact_card_summary: str,
    conversation_history: str,
    session_state: str,
    valid_transitions: list[str],
    user_message: str,
    tenant_intent: str | None = None,
) -> tuple[str, str]:
    """Monta (system_prompt, user_prompt) no padrão definitivo.

    Args:
        contact_card_summary: Resumo do ContactCard (string sanitizada).
        conversation_history: Histórico curto (string sanitizada).
        session_state: Estado atual.
        valid_transitions: Lista de transições válidas.
        user_message: Mensagem atual do usuário.
        tenant_intent: Vertente detectada (opcional).
    """
    contexts = build_contexts(tenant_intent)
    system_prompt = contexts["system_context"]

    user_prompt = format_otto_prompt(
        user_message=user_message,
        session_state=session_state,
        valid_transitions=valid_transitions,
        institutional_context=contexts["institutional_context"],
        tenant_context=contexts["tenant_context"],
        contact_card_summary=contact_card_summary,
        conversation_history=conversation_history,
    )

    return system_prompt, user_prompt
