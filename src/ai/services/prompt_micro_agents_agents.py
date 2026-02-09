"""Execução dos micro agentes especializados de contexto."""

from __future__ import annotations

import logging
from typing import Any

from ai.config.prompt_assets_loader import load_prompt_template
from ai.services.prompt_micro_agents_cases import select_case
from ai.services.prompt_micro_agents_context import context_exists, context_path
from ai.services.prompt_micro_agents_text import extract_numbers, format_roi_inputs
from ai.services.prompt_micro_agents_types import MicroAgentResult

logger = logging.getLogger(__name__)


async def objection_agent(
    *,
    folder: str,
    objection_types: list[str],
    correlation_id: str | None,
) -> MicroAgentResult:
    """Seleciona contexto de objeções quando aplicável."""
    path = context_path(folder, "objections.yaml")
    if not context_exists(path):
        return MicroAgentResult.empty()
    logger.info(
        "micro_agent_objection",
        extra={
            "component": "prompt_micro_agents",
            "action": "select_objection_context",
            "result": "ok",
            "correlation_id": correlation_id,
            "vertical": folder,
            "objection_types": objection_types,
        },
    )
    return MicroAgentResult(
        context_paths=[path],
        context_chunks=[],
        loaded_contexts=[path],
    )


async def case_agent(
    *,
    folder: str,
    normalized_message: str,
    contact_card_signals: dict[str, Any],
    correlation_id: str | None,
) -> MicroAgentResult:
    """Seleciona case da vertical e retorna contexto correspondente."""
    selection = select_case(folder, normalized_message, contact_card_signals)
    if not selection.case_id:
        return MicroAgentResult.empty()
    logger.info(
        "micro_agent_case_selected",
        extra={
            "component": "prompt_micro_agents",
            "action": "select_case",
            "result": "ok",
            "correlation_id": correlation_id,
            "vertical": folder,
            "case_id": selection.case_id,
            "confidence": selection.confidence,
        },
    )
    path = context_path(folder, f"cases/{selection.case_id}.yaml")
    if not context_exists(path):
        return MicroAgentResult.empty()
    return MicroAgentResult(context_paths=[path], context_chunks=[], loaded_contexts=[path])


async def roi_agent(
    *,
    normalized_message: str,
    contact_card_signals: dict[str, Any],
    correlation_id: str | None,
) -> MicroAgentResult:
    """Gera hint textual de ROI a partir de sinais coletados."""
    roi_inputs = format_roi_inputs(normalized_message, contact_card_signals)
    signal_keys = [
        key
        for key in ("company_size", "budget_indication", "specific_need")
        if contact_card_signals.get(key)
    ]
    has_numbers = bool(extract_numbers(normalized_message))
    logger.info(
        "micro_agent_roi_hint",
        extra={
            "component": "prompt_micro_agents",
            "action": "build_roi_hint",
            "result": "ok",
            "correlation_id": correlation_id,
            "signal_keys": signal_keys,
            "has_numbers": has_numbers,
        },
    )
    template = load_prompt_template("roi_hint_template.yaml")
    return MicroAgentResult(
        context_paths=[],
        context_chunks=[template.format(roi_inputs=roi_inputs)],
        loaded_contexts=[],
    )
