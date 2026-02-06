"""Micro agentes para injeções dinâmicas de contexto."""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ai.config.prompt_assets_loader import load_prompt_template
from ai.prompts.context_builder import normalize_tenant_intent

_VERTENTES_DIR = Path(__file__).resolve().parents[1] / "contexts" / "vertentes"
logger = logging.getLogger(__name__)

_COMPETITORS = (
    "manychat",
    "chatfuel",
    "blip",
    "take blip",
    "zenvia",
    "rd station",
    "hubspot",
    "intercom",
    "zendesk",
    "freshchat",
    "twilio",
)

_PRICE_OBJECTION_RE = re.compile(
    r"\b("
    r"muito caro|caro demais|carissimo|caro|absurdo|inviavel|nao compensa|"
    r"nao vale|fora do orcamento|estoura o orcamento|salgado|puxado|pesado"
    r")\b"
)
_COMPARISON_OBJECTION_RE = re.compile(
    r"\b("
    r"ja uso|ja tenho|uso|tenho"
    r")\b.*\b("
    r"bot|plataforma|sistema|"
    + "|".join(re.escape(name) for name in _COMPETITORS)
    + r")\b"
)
_TRUST_OBJECTION_RE = re.compile(
    r"\b("
    r"medo|nao confio|funciona mesmo|garante|err(ar|a)|responder errado|alucin"
    r"|vai dar problema|risco"
    r")\b"
)
_TIMING_OBJECTION_RE = re.compile(
    r"\b("
    r"demora|muito tempo|prazo longo|urgente|pra ontem|nao posso esperar"
    r")\b"
)

_CASE_RE = re.compile(
    r"\b(case|exemplo|resultado|cliente|prova social|funcionou|deu certo|sucesso)\b"
)

_ROI_RE = re.compile(
    r"\b("
    r"roi|retorno|payback|investimento|custo|orcamento|preco|valor|mensalidade|"
    r"quanto custa|quanto sai|quanto fica|economia"
    r")\b"
)


@dataclass(frozen=True, slots=True)
class MicroAgentResult:
    context_paths: list[str]
    context_chunks: list[str]
    loaded_contexts: list[str]

    @classmethod
    def empty(cls) -> MicroAgentResult:
        return cls(context_paths=[], context_chunks=[], loaded_contexts=[])


@dataclass(frozen=True, slots=True)
class CaseSelection:
    case_id: str | None
    confidence: float


async def run_prompt_micro_agents(
    *,
    tenant_intent: str | None,
    intent_confidence: float,
    user_message: str,
    contact_card_signals: dict[str, Any] | None = None,
    session_state: str | None = None,
) -> MicroAgentResult:
    folder = normalize_tenant_intent(tenant_intent)
    if not folder or session_state == "HANDOFF_HUMAN":
        return MicroAgentResult.empty()

    msg = _normalize(user_message)
    if not msg:
        return MicroAgentResult.empty()

    objection_types = _detect_objection_types(msg)
    run_objection = bool(objection_types) and intent_confidence >= 0.4
    run_case = _should_run_case(msg)
    run_roi = _should_run_roi(msg, contact_card_signals)

    logger.info(
        "micro_agents_gate",
        extra={
            "vertical": folder,
            "run_objection": run_objection,
            "run_case": run_case,
            "run_roi": run_roi,
            "objection_types": objection_types,
        },
    )

    tasks: list[asyncio.Future[MicroAgentResult]] = []
    if run_objection:
        tasks.append(asyncio.create_task(_objection_agent(folder, objection_types)))
    if run_case:
        tasks.append(asyncio.create_task(_case_agent(folder, msg, contact_card_signals)))
    if run_roi:
        tasks.append(asyncio.create_task(_roi_agent(msg, contact_card_signals)))

    if not tasks:
        return MicroAgentResult.empty()

    results = await asyncio.gather(*tasks, return_exceptions=False)
    merged = _merge_results(results)

    if merged.context_paths or merged.context_chunks:
        logger.info(
            "micro_agents_injected",
            extra={
                "vertical": folder,
                "context_paths": merged.context_paths,
                "loaded_contexts": merged.loaded_contexts,
                "chunk_count": len(merged.context_chunks),
            },
        )

    return merged


def _merge_results(results: list[MicroAgentResult]) -> MicroAgentResult:
    context_paths: list[str] = []
    context_chunks: list[str] = []
    loaded_contexts: list[str] = []

    for result in results:
        for path in result.context_paths:
            if path and path not in context_paths:
                context_paths.append(path)
        for chunk in result.context_chunks:
            if chunk and chunk not in context_chunks:
                context_chunks.append(chunk)
        for path in result.loaded_contexts:
            if path and path not in loaded_contexts:
                loaded_contexts.append(path)

    return MicroAgentResult(
        context_paths=context_paths,
        context_chunks=context_chunks,
        loaded_contexts=loaded_contexts,
    )


def _detect_objection_types(normalized_message: str) -> list[str]:
    types: list[str] = []
    if _PRICE_OBJECTION_RE.search(normalized_message):
        types.append("price")
    if _COMPARISON_OBJECTION_RE.search(normalized_message):
        types.append("comparison")
    if _TRUST_OBJECTION_RE.search(normalized_message):
        types.append("trust")
    if _TIMING_OBJECTION_RE.search(normalized_message):
        types.append("timing")
    return types


def _should_run_case(normalized_message: str) -> bool:
    return bool(_CASE_RE.search(normalized_message))


def _should_run_roi(
    normalized_message: str,
    contact_card_signals: dict[str, Any] | None,
) -> bool:
    if not _ROI_RE.search(normalized_message):
        return False
    if not contact_card_signals:
        return True
    return bool(
        contact_card_signals.get("company_size")
        or contact_card_signals.get("budget_indication")
        or contact_card_signals.get("specific_need")
    )


async def _objection_agent(folder: str, objection_types: list[str]) -> MicroAgentResult:
    path = _context_path(folder, "objections.yaml")
    if not _context_exists(path):
        return MicroAgentResult.empty()
    logger.info(
        "micro_agent_objection",
        extra={
            "vertical": folder,
            "objection_types": objection_types,
        },
    )
    return MicroAgentResult(
        context_paths=[path],
        context_chunks=[],
        loaded_contexts=[path],
    )


async def _case_agent(
    folder: str,
    normalized_message: str,
    contact_card_signals: dict[str, Any] | None,
) -> MicroAgentResult:
    selection = _select_case(folder, normalized_message, contact_card_signals or {})
    if not selection.case_id:
        return MicroAgentResult.empty()
    logger.info(
        "micro_agent_case_selected",
        extra={
            "vertical": folder,
            "case_id": selection.case_id,
            "confidence": selection.confidence,
        },
    )
    path = _context_path(folder, f"cases/{selection.case_id}.yaml")
    if not _context_exists(path):
        return MicroAgentResult.empty()
    return MicroAgentResult(
        context_paths=[path],
        context_chunks=[],
        loaded_contexts=[path],
    )


async def _roi_agent(
    normalized_message: str,
    contact_card_signals: dict[str, Any] | None,
) -> MicroAgentResult:
    signals = contact_card_signals or {}
    roi_inputs = _format_roi_inputs(normalized_message, signals)
    signal_keys = [key for key in ("company_size", "budget_indication", "specific_need") if signals.get(key)]
    has_numbers = bool(_extract_numbers(normalized_message))
    logger.info(
        "micro_agent_roi_hint",
        extra={
            "signal_keys": signal_keys,
            "has_numbers": has_numbers,
        },
    )
    template = load_prompt_template("roi_hint_template.yaml")
    chunk = template.format(roi_inputs=roi_inputs)
    return MicroAgentResult(
        context_paths=[],
        context_chunks=[chunk],
        loaded_contexts=[],
    )


def _select_case(
    folder: str,
    normalized_message: str,
    contact_card_signals: dict[str, Any],
) -> CaseSelection:
    index_path = _cases_index_path(folder)
    if not index_path.exists():
        return CaseSelection(case_id=None, confidence=0.0)

    data = _load_yaml(index_path)
    cases = data.get("cases") if isinstance(data, dict) else None
    if not isinstance(cases, list) or not cases:
        return CaseSelection(case_id=None, confidence=0.0)

    message_tokens = normalized_message
    extra_text = " ".join(
        str(contact_card_signals.get(key, "")).lower()
        for key in ("specific_need", "company", "role")
        if contact_card_signals.get(key)
    )
    extra_text = _normalize(extra_text)

    best_id: str | None = None
    best_score = 0
    default_id: str | None = None

    for item in cases:
        if not isinstance(item, dict):
            continue
        case_id = str(item.get("id") or "").strip()
        if not case_id:
            continue
        if item.get("default") is True and not default_id:
            default_id = case_id
        keywords = item.get("keywords") or item.get("segments") or []
        if not isinstance(keywords, list):
            keywords = []
        score = 0
        for key in keywords:
            key_norm = _normalize(str(key))
            if not key_norm:
                continue
            if key_norm in message_tokens:
                score += 2
            elif extra_text and key_norm in extra_text:
                score += 1
        if score > best_score:
            best_score = score
            best_id = case_id

    if best_id:
        confidence = 0.8 if best_score >= 3 else 0.6
        return CaseSelection(case_id=best_id, confidence=confidence)
    if default_id:
        return CaseSelection(case_id=default_id, confidence=0.4)
    return CaseSelection(case_id=None, confidence=0.0)


def _format_roi_inputs(normalized_message: str, contact_card_signals: dict[str, Any]) -> str:
    parts: list[str] = []
    if company_size := contact_card_signals.get("company_size"):
        parts.append(f"porte={company_size}")
    if budget := contact_card_signals.get("budget_indication"):
        parts.append(f"orcamento={budget}")
    if need := contact_card_signals.get("specific_need"):
        parts.append(f"necessidade={need}")
    numbers = _extract_numbers(normalized_message)
    if numbers:
        parts.append(f"numeros={', '.join(numbers)}")
    if not parts:
        return "sem dados adicionais"
    return "; ".join(parts)


def _extract_numbers(normalized_message: str) -> list[str]:
    raw = re.findall(r"\b\d+(?:[.,]\d+)?(?:k)?\b", normalized_message)
    return [item for item in raw if item]


def _cases_index_path(folder: str) -> Path:
    return _VERTENTES_DIR / folder / "cases" / "index.yaml"


def _context_path(folder: str, relative: str) -> str:
    return f"vertentes/{folder}/{relative}"


def _context_exists(relative_path: str) -> bool:
    try:
        rel = Path(relative_path)
        if rel.is_absolute():
            return False
        if ".." in rel.parts:
            return False
        path = (_VERTENTES_DIR / rel.relative_to("vertentes")).resolve()
    except Exception:
        return False
    return path.exists()


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _normalize(text: str) -> str:
    lowered = (text or "").strip().lower()
    if not lowered:
        return ""
    no_accents = "".join(
        ch for ch in unicodedata.normalize("NFKD", lowered) if not unicodedata.combining(ch)
    )
    return " ".join(no_accents.split())
