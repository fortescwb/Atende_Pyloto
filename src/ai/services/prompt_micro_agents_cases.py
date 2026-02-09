"""Seleção de cases para micro agente de prova social."""

from __future__ import annotations

from typing import Any

from ai.services.prompt_micro_agents_context import cases_index_path, load_yaml
from ai.services.prompt_micro_agents_text import normalize
from ai.services.prompt_micro_agents_types import CaseSelection


def select_case(
    folder: str,
    normalized_message: str,
    contact_card_signals: dict[str, Any],
) -> CaseSelection:
    """Seleciona melhor case com base em tokens da mensagem e sinais do contato."""
    cases = _load_cases(folder)
    if not cases:
        return CaseSelection(case_id=None, confidence=0.0)

    extra_text = _build_extra_text(contact_card_signals)
    best_id: str | None = None
    best_score = 0
    default_id: str | None = None
    for item in cases:
        case_id, keywords, is_default = _parse_case_item(item)
        if not case_id:
            continue
        if is_default and not default_id:
            default_id = case_id
        score = _score_case_keywords(
            keywords=keywords,
            normalized_message=normalized_message,
            extra_text=extra_text,
        )
        if score > best_score:
            best_score = score
            best_id = case_id

    if best_id:
        confidence = 0.8 if best_score >= 3 else 0.6
        return CaseSelection(case_id=best_id, confidence=confidence)
    if default_id:
        return CaseSelection(case_id=default_id, confidence=0.4)
    return CaseSelection(case_id=None, confidence=0.0)


def _load_cases(folder: str) -> list[Any]:
    index_path = cases_index_path(folder)
    if not index_path.exists():
        return []
    data = load_yaml(index_path)
    cases = data.get("cases") if isinstance(data, dict) else None
    return cases if isinstance(cases, list) else []


def _build_extra_text(contact_card_signals: dict[str, Any]) -> str:
    raw = " ".join(
        str(contact_card_signals.get(key, "")).lower()
        for key in ("specific_need", "company", "role")
        if contact_card_signals.get(key)
    )
    return normalize(raw)


def _parse_case_item(item: Any) -> tuple[str, list[Any], bool]:
    if not isinstance(item, dict):
        return "", [], False
    case_id = str(item.get("id") or "").strip()
    keywords = item.get("keywords") or item.get("segments") or []
    if not isinstance(keywords, list):
        keywords = []
    return case_id, keywords, item.get("default") is True


def _score_case_keywords(
    *,
    keywords: list[Any],
    normalized_message: str,
    extra_text: str,
) -> int:
    score = 0
    for key in keywords:
        key_norm = normalize(str(key))
        if not key_norm:
            continue
        if key_norm in normalized_message:
            score += 2
        elif extra_text and key_norm in extra_text:
            score += 1
    return score
