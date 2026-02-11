"""Execução dos micro agentes especializados de contexto.

P0-2: Todos os agentes são resilientes a YAML faltante ou erros de carregamento,
retornando MicroAgentResult.empty() em caso de falha.
"""

from __future__ import annotations

import logging
from typing import Any

from ai.services.prompt_micro_agents_cases import select_case
from ai.services.prompt_micro_agents_context import context_exists, context_path
from ai.services.prompt_micro_agents_text import extract_numbers
from ai.services.prompt_micro_agents_types import MicroAgentResult

logger = logging.getLogger(__name__)


async def objection_agent(
    *,
    folder: str,
    objection_types: list[str],
    correlation_id: str | None,
) -> MicroAgentResult:
    """Seleciona contexto de objeções quando aplicável.

    P0-2: Resiliente a YAML faltante - retorna empty em caso de falha.
    """
    try:
        path = context_path(folder, "objections.yaml")
        if not context_exists(path):
            logger.warning(
                "objection_yaml_missing",
                extra={
                    "component": "prompt_micro_agents",
                    "action": "select_objection_context",
                    "result": "missing",
                    "correlation_id": correlation_id,
                    "vertical": folder,
                    "path": path,
                },
            )
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
    except Exception as exc:
        logger.warning(
            "objection_agent_error",
            extra={
                "component": "prompt_micro_agents",
                "action": "select_objection_context",
                "result": "error",
                "correlation_id": correlation_id,
                "vertical": folder,
                "error_type": type(exc).__name__,
            },
        )
        return MicroAgentResult.empty()


async def case_agent(
    *,
    folder: str,
    normalized_message: str,
    contact_card_signals: dict[str, Any],
    correlation_id: str | None,
) -> MicroAgentResult:
    """Seleciona case da vertical e retorna contexto correspondente.

    P0-2: Resiliente a YAML faltante - retorna empty em caso de falha.
    """
    try:
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
            logger.warning(
                "case_yaml_missing",
                extra={
                    "component": "prompt_micro_agents",
                    "action": "select_case",
                    "result": "missing",
                    "correlation_id": correlation_id,
                    "vertical": folder,
                    "case_id": selection.case_id,
                    "path": path,
                },
            )
            return MicroAgentResult.empty()
        return MicroAgentResult(context_paths=[path], context_chunks=[], loaded_contexts=[path])
    except Exception as exc:
        logger.warning(
            "case_agent_error",
            extra={
                "component": "prompt_micro_agents",
                "action": "select_case",
                "result": "error",
                "correlation_id": correlation_id,
                "vertical": folder,
                "error_type": type(exc).__name__,
            },
        )
        return MicroAgentResult.empty()


async def roi_agent(
    *,
    folder: str,
    normalized_message: str,
    contact_card_signals: dict[str, Any],
    correlation_id: str | None,
) -> MicroAgentResult:
    """Carrega contexto de ROI hints da vertente quando aplicável.

    P1-1: Refatorado para carregar YAML da vertente ao invés de gerar inline.
    P0-2: Resiliente a YAML faltante - retorna empty em caso de falha.
    """
    try:
        path = context_path(folder, "roi_hints.yaml")
        if not context_exists(path):
            logger.warning(
                "roi_yaml_missing",
                extra={
                    "component": "prompt_micro_agents",
                    "action": "select_roi_context",
                    "result": "missing",
                    "correlation_id": correlation_id,
                    "vertical": folder,
                    "path": path,
                },
            )
            return MicroAgentResult.empty()
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
                "action": "select_roi_context",
                "result": "ok",
                "correlation_id": correlation_id,
                "vertical": folder,
                "signal_keys": signal_keys,
                "has_numbers": has_numbers,
            },
        )
        return MicroAgentResult(
            context_paths=[path],
            context_chunks=[],
            loaded_contexts=[path],
        )
    except Exception as exc:
        logger.warning(
            "roi_agent_error",
            extra={
                "component": "prompt_micro_agents",
                "action": "select_roi_context",
                "result": "error",
                "correlation_id": correlation_id,
                "vertical": folder,
                "error_type": type(exc).__name__,
            },
        )
        return MicroAgentResult.empty()
