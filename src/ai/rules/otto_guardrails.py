"""Guardrails deterministicas do OttoAgent."""

from __future__ import annotations

import re
from collections.abc import Iterable

from ai.config.institutional_loader import load_institutional_context
from ai.utils.sanitizer import contains_pii

_PROMISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bgarant\w+", re.IGNORECASE),
    re.compile(r"\b(entrego|entregamos|entrega)\s+em\s+\d+", re.IGNORECASE),
    re.compile(r"\bcome(c|\xE7)amos\s+amanh(a|\xE3)", re.IGNORECASE),
    re.compile(r"\b(preco|pre\xE7o|custo|custa)\s+r\$", re.IGNORECASE),
    re.compile(r"\b(valor|preco|pre\xE7o)\s+fechado\b", re.IGNORECASE),
    re.compile(r"\bresultado\s+garantid\w+", re.IGNORECASE),
    re.compile(r"\bmelhor\s+que\b", re.IGNORECASE),
)


def is_response_length_valid(text: str, *, max_chars: int = 500) -> bool:
    """Valida tamanho de resposta."""
    if not text:
        return False
    return len(text) <= max_chars


def contains_prohibited_promises(text: str) -> bool:
    """Verifica indicios de promessas proibidas."""
    if not text:
        return False

    text_lower = text.lower()

    # Checagem por padroes genericos
    if any(pattern.search(text) for pattern in _PROMISE_PATTERNS):
        return True

    # Checagem por exemplos explicitos do contexto institucional
    examples = _extract_prohibited_examples()
    return any(example in text_lower for example in examples)


def contains_disallowed_pii(text: str) -> bool:
    """Detecta PII no texto, ignorando contatos institucionais permitidos."""
    if not text:
        return False

    allowed = _collect_allowed_contacts(load_institutional_context())
    scrubbed = _strip_allowed_contacts(text, allowed)
    return contains_pii(scrubbed)


def _extract_prohibited_examples() -> list[str]:
    context = load_institutional_context()
    politicas = context.get("politicas", {})
    compromissos = politicas.get("compromissos_proibidos", {})
    nao_prometer = compromissos.get("nao_prometer", [])
    examples: list[str] = []
    for item in nao_prometer:
        if not isinstance(item, str):
            continue
        match = re.findall(r"\('(.*?)'\)", item)
        for example in match:
            examples.append(example.lower())
    return examples


def _collect_allowed_contacts(context: dict[str, object]) -> set[str]:
    allowed: set[str] = set()
    contato = context.get("contato", {})
    if isinstance(contato, dict):
        for value in contato.values():
            _collect_strings(value, allowed)
    return {item for item in allowed if item}


def _collect_strings(value: object, output: set[str]) -> None:
    if isinstance(value, str):
        output.add(value)
        return
    if isinstance(value, dict):
        for inner in value.values():
            _collect_strings(inner, output)
        return
    if isinstance(value, Iterable):
        for inner in value:
            _collect_strings(inner, output)


def _strip_allowed_contacts(text: str, allowed: set[str]) -> str:
    sanitized = text
    for item in allowed:
        sanitized = _replace_case_insensitive(sanitized, item)
        digits = re.sub(r"\D", "", item)
        if digits:
            sanitized = sanitized.replace(digits, "")
    return sanitized


def _replace_case_insensitive(text: str, value: str) -> str:
    if not value:
        return text
    return re.sub(re.escape(value), "", text, flags=re.IGNORECASE)
