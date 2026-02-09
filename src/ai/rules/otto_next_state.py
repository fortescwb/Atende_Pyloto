"""Normalizacao deterministica do next_state do Otto."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

_QUESTION_PREFIXES = (
    "qual ",
    "quais ",
    "quanto",
    "quantos ",
    "quantas ",
    "como ",
    "voce ",
    "voces ",
    "ja ",
    "tem ",
    "usa ",
    "pode ",
    "podemos ",
    "poderia ",
)


def detect_has_new_question(text: str) -> bool:
    """Heuristica simples para identificar se a resposta contem pergunta."""
    normalized = " ".join((text or "").strip().lower().split())
    if not normalized:
        return False
    if "?" in normalized:
        return True
    return normalized.startswith(_QUESTION_PREFIXES)


def normalize_next_state(
    *,
    proposed_state: str,
    valid_transitions: Iterable[str] | None,
    has_new_question: bool,
    requires_human: bool,
) -> str:
    """Normaliza next_state usando regras deterministicas e transicoes validas."""
    valid = {state for state in (valid_transitions or []) if state}
    if requires_human:
        if "HANDOFF_HUMAN" in valid:
            return "HANDOFF_HUMAN"
        return proposed_state

    if not valid:
        return proposed_state

    if has_new_question:
        if "COLLECTING_INFO" in valid:
            return "COLLECTING_INFO"
        if "TRIAGE" in valid:
            return "TRIAGE"
        return proposed_state

    if "SELF_SERVE_INFO" in valid:
        return "SELF_SERVE_INFO"
    if "GENERATING_RESPONSE" in valid:
        return "GENERATING_RESPONSE"
    return proposed_state
