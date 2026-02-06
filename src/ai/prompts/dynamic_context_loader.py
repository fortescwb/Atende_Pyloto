"""Loader de contextos dinâmicos por triggers de keywords."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ai.config.prompt_assets_loader import load_context_for_prompt
from ai.prompts.context_builder import normalize_tenant_intent

_VERTENTES_DIR = Path(__file__).resolve().parents[1] / "contexts" / "vertentes"


@dataclass(frozen=True, slots=True)
class DynamicContextResult:
    """Resultado da resolução de contextos dinâmicos."""

    contexts_for_prompt: list[str]
    loaded_contexts: list[str]


def resolve_dynamic_contexts(
    *,
    tenant_intent: str | None,
    user_message: str,
    intent_confidence: float = 0.0,
    loaded_contexts: list[str] | None = None,
    session_state: str | None = None,
) -> DynamicContextResult:
    """Resolve contextos dinâmicos para o turno atual.

    Regras:
      - Contextos com `persist: true` permanecem em `loaded_contexts`.
      - Contextos com `persist: false` só entram no prompt atual.
      - Se `session_state == HANDOFF_HUMAN`, limpa tudo.
      - Se a vertente mudar, descarta contextos anteriores.
    """
    folder = normalize_tenant_intent(tenant_intent)
    if not folder:
        return DynamicContextResult(contexts_for_prompt=[], loaded_contexts=[])
    if session_state == "HANDOFF_HUMAN":
        return DynamicContextResult(contexts_for_prompt=[], loaded_contexts=[])
    msg = _normalize(user_message)

    vert_dir = _VERTENTES_DIR / folder
    if not vert_dir.exists():
        return DynamicContextResult(contexts_for_prompt=[], loaded_contexts=[])

    existing = _filter_loaded_contexts(loaded_contexts or [], folder)
    persistent: list[str] = list(existing)
    transient: list[str] = []
    if msg:
        for path in sorted(vert_dir.glob("*.yaml")):
            if path.name == "core.yaml":
                continue
            meta = _load_context_meta(path)
            if meta is None:
                continue
            if _should_inject(meta, msg, intent_confidence):
                rel_path = f"vertentes/{folder}/{path.name}"
                if meta.persist:
                    if rel_path not in persistent:
                        persistent.append(rel_path)
                else:
                    transient.append(rel_path)

    contexts_for_prompt = _load_contexts_in_order(persistent, transient)
    return DynamicContextResult(
        contexts_for_prompt=contexts_for_prompt,
        loaded_contexts=sorted(set(persistent)),
    )


@dataclass(frozen=True, slots=True)
class _ContextMeta:
    trigger: dict[str, Any] | None
    persist: bool
    min_confidence: float


def _load_context_meta(path: Path) -> _ContextMeta | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    metadata = data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {}
    if bool(metadata.get("manual_injection", False)):
        return _ContextMeta(
            trigger=None,
            persist=bool(metadata.get("persist", False)),
            min_confidence=float(metadata.get("min_confidence", 0.0)),
        )
    trigger = metadata.get("injection_trigger") or data.get("injection_trigger")
    persist = bool(metadata.get("persist", False))
    min_confidence = float(metadata.get("min_confidence", 0.0))
    return _ContextMeta(
        trigger=trigger if isinstance(trigger, dict) else None,
        persist=persist,
        min_confidence=min_confidence,
    )


def _should_inject(meta: _ContextMeta, normalized_message: str, intent_confidence: float) -> bool:
    if meta.min_confidence and intent_confidence < meta.min_confidence:
        return False
    if meta.trigger is None:
        return False
    return _matches_trigger(meta.trigger, normalized_message)


def _matches_trigger(trigger: dict[str, Any], normalized_message: str) -> bool:
    any_keywords = trigger.get("any_keywords") or trigger.get("keywords")
    all_keywords = trigger.get("all_keywords")

    if isinstance(any_keywords, list) and any_keywords:
        return any(_normalize(word) in normalized_message for word in any_keywords if word)

    if isinstance(all_keywords, list) and all_keywords:
        return all(_normalize(word) in normalized_message for word in all_keywords if word)

    return False


def _filter_loaded_contexts(contexts: list[str], folder: str) -> list[str]:
    prefix = f"vertentes/{folder}/"
    return [ctx for ctx in contexts if ctx.startswith(prefix)]


def _load_contexts_in_order(persistent: list[str], transient: list[str]) -> list[str]:
    rel_paths: list[str] = []
    for path in persistent:
        if path not in rel_paths:
            rel_paths.append(path)
    for path in transient:
        if path not in rel_paths:
            rel_paths.append(path)
    return [load_context_for_prompt(path) for path in rel_paths]


def _normalize(text: str) -> str:
    lowered = (text or "").strip().lower()
    if not lowered:
        return ""
    no_accents = "".join(
        ch for ch in unicodedata.normalize("NFKD", lowered) if not unicodedata.combining(ch)
    )
    return " ".join(no_accents.split())
