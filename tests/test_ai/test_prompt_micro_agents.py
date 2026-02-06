"""Testes dos micro agentes de contexto."""

from __future__ import annotations

import pytest

from ai.services.prompt_micro_agents import run_prompt_micro_agents


@pytest.mark.asyncio
async def test_objection_micro_agent_injects_objections() -> None:
    result = await run_prompt_micro_agents(
        tenant_intent="automacao",
        intent_confidence=0.6,
        user_message="Achei muito caro, já uso ManyChat.",
        contact_card_signals={},
    )
    assert "vertentes/automacao/objections.yaml" in result.context_paths
    assert "vertentes/automacao/objections.yaml" in result.loaded_contexts


@pytest.mark.asyncio
async def test_case_selector_picks_segment_case() -> None:
    result = await run_prompt_micro_agents(
        tenant_intent="automacao",
        intent_confidence=0.6,
        user_message="Tem algum case de clínica?",
        contact_card_signals={},
    )
    assert "vertentes/automacao/cases/clinica.yaml" in result.context_paths


@pytest.mark.asyncio
async def test_roi_agent_injects_hint() -> None:
    result = await run_prompt_micro_agents(
        tenant_intent="automacao",
        intent_confidence=0.6,
        user_message="Qual o ROI e quanto custa?",
        contact_card_signals={"company_size": "pequena"},
    )
    assert any("ROI" in chunk for chunk in result.context_chunks)
