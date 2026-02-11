"""Micro agentes para injeções dinâmicas de contexto."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ai.prompts.context_builder import normalize_tenant_intent
from ai.services.prompt_micro_agents_agents import case_agent, objection_agent, roi_agent
from ai.services.prompt_micro_agents_text import (
    detect_objection_types,
    normalize,
    should_run_case,
    should_run_roi,
)
from ai.services.prompt_micro_agents_types import (
    CaseSelection,
    MicroAgentResult,
    merge_results,
)

logger = logging.getLogger(__name__)


async def run_prompt_micro_agents(
    *,
    tenant_intent: str | None,
    intent_confidence: float,
    user_message: str,
    contact_card_signals: dict[str, Any] | None = None,
    session_state: str | None = None,
    correlation_id: str | None = None,
) -> MicroAgentResult:
    """Executa micro agentes de contexto em paralelo quando elegíveis."""
    folder, normalized_message = _resolve_folder_and_message(
        tenant_intent,
        session_state,
        user_message,
    )
    if not folder or not normalized_message:
        return MicroAgentResult.empty()

    signals = contact_card_signals or {}
    gate = _evaluate_gate(normalized_message, intent_confidence, signals)
    _log_gate(folder=folder, gate=gate, correlation_id=correlation_id)
    tasks = _build_tasks(
        folder=folder,
        normalized_message=normalized_message,
        signals=signals,
        gate=gate,
        correlation_id=correlation_id,
    )
    if not tasks:
        return MicroAgentResult.empty()

    merged = merge_results(await asyncio.gather(*tasks, return_exceptions=False))
    _log_injected_contexts(folder=folder, merged=merged, correlation_id=correlation_id)
    return merged


__all__ = ["CaseSelection", "MicroAgentResult", "run_prompt_micro_agents"]


def _resolve_folder_and_message(
    tenant_intent: str | None,
    session_state: str | None,
    user_message: str,
) -> tuple[str, str]:
    folder = normalize_tenant_intent(tenant_intent) or ""
    if not folder or session_state == "HANDOFF_HUMAN":
        return "", ""
    return folder, normalize(user_message)


def _evaluate_gate(
    normalized_message: str,
    intent_confidence: float,
    signals: dict[str, Any],
) -> dict[str, Any]:
    objection_types = detect_objection_types(normalized_message)
    return {
        "objection_types": objection_types,
        "run_objection": bool(objection_types) and intent_confidence >= 0.4,
        "run_case": should_run_case(normalized_message),
        "run_roi": should_run_roi(normalized_message, signals),
    }


def _log_gate(*, folder: str, gate: dict[str, Any], correlation_id: str | None) -> None:
    logger.info(
        "micro_agents_gate",
        extra={
            "component": "prompt_micro_agents",
            "action": "gate",
            "result": "evaluated",
            "correlation_id": correlation_id,
            "vertical": folder,
            "run_objection": gate["run_objection"],
            "run_case": gate["run_case"],
            "run_roi": gate["run_roi"],
            "objection_types": gate["objection_types"],
        },
    )


def _build_tasks(
    *,
    folder: str,
    normalized_message: str,
    signals: dict[str, Any],
    gate: dict[str, Any],
    correlation_id: str | None,
) -> list[asyncio.Task[MicroAgentResult]]:
    tasks: list[asyncio.Task[MicroAgentResult]] = []
    if gate["run_objection"]:
        tasks.append(
            asyncio.create_task(
                objection_agent(
                    folder=folder,
                    objection_types=gate["objection_types"],
                    correlation_id=correlation_id,
                )
            )
        )
    if gate["run_case"]:
        tasks.append(
            asyncio.create_task(
                case_agent(
                    folder=folder,
                    normalized_message=normalized_message,
                    contact_card_signals=signals,
                    correlation_id=correlation_id,
                )
            )
        )
    if gate["run_roi"]:
        tasks.append(
            asyncio.create_task(
                roi_agent(
                    folder=folder,
                    normalized_message=normalized_message,
                    contact_card_signals=signals,
                    correlation_id=correlation_id,
                )
            )
        )
    return tasks


def _log_injected_contexts(
    *,
    folder: str,
    merged: MicroAgentResult,
    correlation_id: str | None,
) -> None:
    if not (merged.context_paths or merged.context_chunks):
        return
    logger.info(
        "micro_agents_injected",
        extra={
            "component": "prompt_micro_agents",
            "action": "inject_context",
            "result": "ok",
            "correlation_id": correlation_id,
            "vertical": folder,
            "context_paths": merged.context_paths,
            "loaded_contexts": merged.loaded_contexts,
            "chunk_count": len(merged.context_chunks),
        },
    )
