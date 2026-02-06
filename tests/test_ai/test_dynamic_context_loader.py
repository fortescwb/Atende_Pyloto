"""Testes do loader de contextos dinâmicos."""

from __future__ import annotations

from ai.prompts.dynamic_context_loader import resolve_dynamic_contexts


def test_dynamic_loader_returns_empty_without_intent() -> None:
    result = resolve_dynamic_contexts(tenant_intent=None, user_message="preço")
    assert result.contexts_for_prompt == []
    assert result.loaded_contexts == []


def test_dynamic_loader_skips_manual_injection() -> None:
    result = resolve_dynamic_contexts(
        tenant_intent="automacao",
        user_message="Achei muito caro, já uso ManyChat.",
        intent_confidence=0.6,
    )
    joined = "\n".join(result.contexts_for_prompt).lower()
    assert "objeções" not in joined
    assert "manychat" not in joined
    assert result.loaded_contexts == []


def test_dynamic_loader_injects_seo_for_trafego() -> None:
    result = resolve_dynamic_contexts(
        tenant_intent="trafego",
        user_message="Quero melhorar SEO e ranquear no Google",
        intent_confidence=0.6,
    )
    joined = "\n".join(result.contexts_for_prompt).lower()
    assert "seo" in joined


def test_dynamic_loader_injects_tech_stack_for_sob_medida() -> None:
    result = resolve_dynamic_contexts(
        tenant_intent="sob_medida",
        user_message="Qual stack/tecnologia vocês usam?",
        intent_confidence=0.6,
    )
    joined = "\n".join(result.contexts_for_prompt).lower()
    assert "stack" in joined or "tecnologia" in joined
