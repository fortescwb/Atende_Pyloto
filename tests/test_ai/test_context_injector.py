"""Testes para ContextInjector."""

from __future__ import annotations

from ai.services.context_injector import ContextInjector


def test_context_injector_maps_legacy_interest() -> None:
    injector = ContextInjector()
    context = injector.build(primary_interest="gestao_perfis")
    assert context
    assert "gestao_perfis_trafego" in context.lower()


def test_context_injector_fallback_empty() -> None:
    injector = ContextInjector()
    assert injector.build(primary_interest=None) == ""
    assert injector.build(primary_interest="inexistente") == ""


def test_context_injector_respects_size_limit() -> None:
    injector = ContextInjector(max_chars=1200)
    context = injector.build(primary_interest="sob_medida")
    assert context
    assert len(context) <= 1200
