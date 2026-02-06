"""Prompt do OttoAgent (agente principal).

Regras:
  - Nenhuma string de prompt vive em `.py`; tudo é carregado de YAML.
  - SYSTEM é composto por contextos sempre carregados (ver `context_builder.py`).
  - USER usa template YAML com placeholders determinísticos.
"""

from __future__ import annotations

from typing import NamedTuple

from ai.config.prompt_assets_loader import load_context_for_prompt, load_prompt_template
from ai.prompts.context_builder import build_contexts
from ai.prompts.dynamic_context_loader import resolve_dynamic_contexts

_OTTO_USER_TEMPLATE = load_prompt_template("otto_user_template.yaml")


def build_otto_system_prompt() -> str:
    """Monta o SYSTEM prompt padronizado do Otto."""
    return build_contexts().get("system_context", "")


OTTO_SYSTEM_PROMPT = build_otto_system_prompt()


class PromptComponents(NamedTuple):
    system_prompt: str
    user_prompt: str
    loaded_contexts: list[str]


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
    intent_confidence: float = 0.0,
    loaded_contexts: list[str] | None = None,
    extra_context_paths: list[str] | None = None,
    extra_context_chunks: list[str] | None = None,
    extra_loaded_contexts: list[str] | None = None,
) -> PromptComponents:
    """Monta (system_prompt, user_prompt, loaded_contexts) no padrão definitivo.

    Args:
        contact_card_summary: Resumo do ContactCard (string sanitizada).
        conversation_history: Histórico curto (string sanitizada).
        session_state: Estado atual.
        valid_transitions: Lista de transições válidas.
        user_message: Mensagem atual do usuário.
        tenant_intent: Vertente detectada (opcional).
        intent_confidence: Confiança na vertente detectada (0.0-1.0).
        loaded_contexts: Contextos persistidos de turnos anteriores.
        extra_context_paths: Caminhos adicionais de contexto para injeção.
        extra_context_chunks: Strings adicionais de contexto para injeção.
        extra_loaded_contexts: Caminhos adicionais a persistir na sessão.
    """
    contexts = build_contexts(tenant_intent)
    system_prompt = contexts["system_context"]

    dynamic_result = resolve_dynamic_contexts(
        tenant_intent=tenant_intent,
        user_message=user_message,
        intent_confidence=intent_confidence,
        loaded_contexts=loaded_contexts,
        session_state=session_state,
    )
    tenant_context = contexts["tenant_context"]
    extra_chunks: list[str] = []
    for path in extra_context_paths or []:
        extra_chunks.append(load_context_for_prompt(path))
    extra_chunks.extend(extra_context_chunks or [])
    tenant_context = _merge_context_chunks(
        [tenant_context] if tenant_context else [],
        dynamic_result.contexts_for_prompt,
        extra_chunks,
    )

    user_prompt = format_otto_prompt(
        user_message=user_message,
        session_state=session_state,
        valid_transitions=valid_transitions,
        institutional_context=contexts["institutional_context"],
        tenant_context=tenant_context,
        contact_card_summary=contact_card_summary,
        conversation_history=conversation_history,
    )

    merged_loaded = sorted(
        set((dynamic_result.loaded_contexts or []) + (extra_loaded_contexts or []))
    )
    return PromptComponents(system_prompt, user_prompt, merged_loaded)


def _merge_context_chunks(*chunks: list[str]) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        for item in chunk or []:
            text = (item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            merged.append(text)
    return "\n\n".join(merged).strip()
