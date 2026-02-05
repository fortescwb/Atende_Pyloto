"""Servico de injecao de contexto vertical (dinamico).

Retorna string curta pronta para prompt, baseada na vertical do lead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai.config.vertical_context_loader import load_vertical_context

_DEFAULT_MAX_CHARS = 1200

_PRIMARY_INTEREST_ALIASES = {
    "gestao_perfis": "gestao_perfis_trafego",
    "trafego_pago": "gestao_perfis_trafego",
    "intermediacao": "intermediacao_entregas",
    "automacao": "automacao_atendimento",
    "sistema_sob_medida": "sob_medida",
}


@dataclass(frozen=True, slots=True)
class ContextInjector:
    """Servico puro para injetar contexto por vertical."""

    max_chars: int = _DEFAULT_MAX_CHARS

    def build(
        self,
        *,
        primary_interest: str | None = None,
        contact_card: Any | None = None,
    ) -> str:
        """Gera contexto vertical pronto para prompt.

        Args:
            primary_interest: ID da vertical (opcional).
            contact_card: ContactCard com primary_interest (opcional).

        Returns:
            String curta pronta para prompt (<= max_chars).
        """
        interest = primary_interest
        if not interest and contact_card is not None:
            interest = getattr(contact_card, "primary_interest", None)

        vertical_id = _normalize_primary_interest(interest or "")
        if not vertical_id:
            return ""

        context = load_vertical_context(vertical_id)
        if not context:
            return ""

        summary = _extract_prompt_summary(context, vertical_id)
        if not summary:
            return ""

        return _truncate(summary, self.max_chars)


def _normalize_primary_interest(value: str) -> str:
    cleaned = value.strip().lower().replace(" ", "_").replace("-", "_")
    return _PRIMARY_INTEREST_ALIASES.get(cleaned, cleaned)


def _extract_prompt_summary(context: dict[str, Any], vertical_id: str) -> str:
    summary = context.get("prompt_summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()

    parts: list[str] = [f"Vertical: {vertical_id}"]

    description = context.get("description")
    if isinstance(description, str) and description.strip():
        parts.append(_compact_text(description, 420))

    target = context.get("target_audience")
    if not isinstance(target, dict):
        target = {}
    ideal = target.get("ideal_customer")
    if isinstance(ideal, list) and ideal:
        items = "; ".join(_compact_text(str(item), 80) for item in ideal[:3])
        if items:
            parts.append(f"Ideal para: {items}")

    pricing_hint = context.get("pricing_hint")
    if isinstance(pricing_hint, str) and pricing_hint.strip():
        parts.append(f"Pricing: {_compact_text(pricing_hint, 160)}")

    return "\n".join(part for part in parts if part).strip()


def _compact_text(text: str, max_chars: int) -> str:
    cleaned = " ".join(text.strip().split())
    if len(cleaned) <= max_chars:
        return cleaned
    snippet = cleaned[:max_chars].rstrip()
    if " " in snippet:
        snippet = snippet.rsplit(" ", 1)[0].rstrip()
    return snippet


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text.strip()
    truncated = text[:max_chars].rstrip()
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0].rstrip()
    return truncated
