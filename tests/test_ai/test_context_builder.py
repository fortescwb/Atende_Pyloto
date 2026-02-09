"""Testes do context builder (montagem de contextos SYSTEM/USER)."""

from __future__ import annotations

from ai.prompts import context_builder


def test_normalize_tenant_intent_aliases() -> None:
    assert context_builder.normalize_tenant_intent("automacao") == "automacao"
    assert context_builder.normalize_tenant_intent("AUTOMACAO_ATENDIMENTO") == "automacao"
    assert context_builder.normalize_tenant_intent("gestao_perfis_trafego") == "trafego"
    assert context_builder.normalize_tenant_intent("desconhecido") is None


def test_build_contexts_dedupes_system_blocks(monkeypatch) -> None:
    fake_assets = {
        "core/system_role.yaml": "A\n\nB",
        "core/mindset.yaml": "B\n\nC",
        "core/guardrails.yaml": "C\n\nD",
        "regras/json_output.yaml": "D\n\nE",
        "core/sobre_pyloto.yaml": "INST",
        "vertentes/automacao/core.yaml": "VERT",
    }

    monkeypatch.setattr(
        context_builder,
        "load_context_for_prompt",
        lambda path: fake_assets[path],
    )

    result = context_builder.build_contexts(tenant_intent="automacao")

    assert result["system_context"] == "A\n\nB\n\nC\n\nD\n\nE"
    assert result["user_context"] == "INST\n\nVERT"


def test_build_contexts_dedupes_shared_user_blocks(monkeypatch) -> None:
    fake_assets = {
        "core/system_role.yaml": "SYSTEM",
        "core/mindset.yaml": "MINDSET",
        "core/guardrails.yaml": "GUARDRAILS",
        "regras/json_output.yaml": "JSON",
        "core/sobre_pyloto.yaml": "BASE\n\nSHARED",
        "vertentes/automacao/core.yaml": "shared\n\nVERT",
    }

    monkeypatch.setattr(
        context_builder,
        "load_context_for_prompt",
        lambda path: fake_assets[path],
    )

    result = context_builder.build_contexts(tenant_intent="automacao")

    assert result["institutional_context"] == "BASE\n\nSHARED"
    assert result["tenant_context"] == "shared\n\nVERT"
    assert result["user_context"] == "BASE\n\nSHARED\n\nVERT"


def test_build_contexts_real_assets_include_required_contexts() -> None:
    result = context_builder.build_contexts(tenant_intent="automacao")
    lowered_system = result["system_context"].lower()

    assert "seu nome: otto" in lowered_system
    assert "mindset comercial" in lowered_system
    assert "guardrails" in lowered_system
    assert "responda somente json" in lowered_system

    lowered_user = result["institutional_context"].lower()
    assert "contato@pyloto.com.br" in lowered_user
