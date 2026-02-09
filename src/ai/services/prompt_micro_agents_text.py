"""Normalização e regras textuais dos micro agentes."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

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


def normalize(text: str) -> str:
    """Normaliza texto removendo acentos e excesso de espaços."""
    lowered = (text or "").strip().lower()
    if not lowered:
        return ""
    no_accents = "".join(
        ch for ch in unicodedata.normalize("NFKD", lowered) if not unicodedata.combining(ch)
    )
    return " ".join(no_accents.split())


def detect_objection_types(normalized_message: str) -> list[str]:
    """Identifica tipos de objeção no texto já normalizado."""
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


def should_run_case(normalized_message: str) -> bool:
    """Define se agente de casos deve rodar."""
    return bool(_CASE_RE.search(normalized_message))


def should_run_roi(
    normalized_message: str,
    contact_card_signals: dict[str, Any] | None,
) -> bool:
    """Define se agente de ROI deve rodar."""
    if not _ROI_RE.search(normalized_message):
        return False
    if not contact_card_signals:
        return True
    return bool(
        contact_card_signals.get("company_size")
        or contact_card_signals.get("budget_indication")
        or contact_card_signals.get("specific_need")
    )


def extract_numbers(normalized_message: str) -> list[str]:
    """Extrai números que podem compor pistas de ROI."""
    return [item for item in re.findall(r"\b\d+(?:[.,]\d+)?(?:k)?\b", normalized_message) if item]


def format_roi_inputs(
    normalized_message: str,
    contact_card_signals: dict[str, Any],
) -> str:
    """Monta string resumida de sinais de ROI para o template."""
    parts: list[str] = []
    if company_size := contact_card_signals.get("company_size"):
        parts.append(f"porte={company_size}")
    if budget := contact_card_signals.get("budget_indication"):
        parts.append(f"orcamento={budget}")
    if need := contact_card_signals.get("specific_need"):
        parts.append(f"necessidade={need}")
    numbers = extract_numbers(normalized_message)
    if numbers:
        parts.append(f"numeros={', '.join(numbers)}")
    return "; ".join(parts) if parts else "sem dados adicionais"
