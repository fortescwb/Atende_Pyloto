"""Servico do ContactCardExtractor (Agente utilitario).

Monta prompt, chama client via protocolo e valida patch resultante.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ai.models.contact_card_extraction import (
    ContactCardExtractionRequest,
    ContactCardExtractionResult,
    ContactCardPatch,
)
from ai.prompts.contact_card_extractor_prompt import (
    CONTACT_CARD_EXTRACTOR_SYSTEM,
    format_contact_card_extractor_prompt,
)

logger = logging.getLogger(__name__)

_PRIMARY_INTEREST_ALIASES = {
    "gestao_perfis": "gestao_perfis_trafego",
    "trafego_pago": "gestao_perfis_trafego",
    "intermediacao": "intermediacao_entregas",
    "automacao": "automacao_atendimento",
}

if TYPE_CHECKING:
    from ai.core.contact_card_extractor_client import ContactCardExtractorClientProtocol


class ContactCardExtractorService:
    """Servico de extração de dados do ContactCard."""

    def __init__(self, client: ContactCardExtractorClientProtocol) -> None:
        self._client = client

    async def extract(
        self,
        request: ContactCardExtractionRequest,
    ) -> ContactCardExtractionResult:
        """Executa extração e retorna patch validado."""
        user_prompt = format_contact_card_extractor_prompt(
            user_message=request.user_message,
            contact_card=request.contact_card_summary,
            conversation_context="\n".join(request.conversation_context or []),
        )

        raw = await self._client.extract(
            system_prompt=CONTACT_CARD_EXTRACTOR_SYSTEM,
            user_prompt=user_prompt,
        )
        if raw is None:
            return ContactCardExtractionResult.empty()

        updates_raw = raw.get("updates") if isinstance(raw, dict) else {}
        updates_raw = self._normalize_raw_updates(updates_raw)
        try:
            patch = ContactCardPatch.model_validate(updates_raw)
        except ValidationError:
            logger.warning("contact_card_patch_invalid")
            return ContactCardExtractionResult.empty()

        patch = self._normalize_patch(patch)
        confidence = _clamp_confidence(
            raw.get("confidence", 0.0) if isinstance(raw, dict) else 0.0
        )
        evidence = (
            raw.get("evidence")
            if isinstance(raw, dict) and isinstance(raw.get("evidence"), list)
            else []
        )

        return ContactCardExtractionResult(
            updates=patch,
            confidence=confidence,
            evidence=evidence,
        )

    @staticmethod
    def _normalize_raw_updates(raw_updates: Any) -> dict[str, Any]:
        if not isinstance(raw_updates, dict):
            return {}

        normalized: dict[str, Any] = {}
        for field, value in raw_updates.items():
            if value is None:
                continue
            if isinstance(value, bool):
                if value:
                    normalized[field] = True
                continue
            if isinstance(value, str):
                cleaned = value.strip()
                if not cleaned:
                    continue
                if field in {"primary_interest", "urgency", "company_size"}:
                    cleaned = cleaned.lower().replace(" ", "_").replace("-", "_")
                    if field == "primary_interest":
                        cleaned = _PRIMARY_INTEREST_ALIASES.get(cleaned, cleaned)
                if field == "email":
                    cleaned = cleaned.lower()
                normalized[field] = cleaned
                continue
            if field == "secondary_interests":
                if isinstance(value, list):
                    items = [str(item).strip() for item in value if str(item).strip()]
                    normalized[field] = items
                elif isinstance(value, str):
                    items = [part.strip() for part in value.split(",") if part.strip()]
                    normalized[field] = items
                continue
            normalized[field] = value

        return normalized

    @staticmethod
    def _normalize_patch(patch: ContactCardPatch) -> ContactCardPatch:
        data = patch.model_dump()
        cleaned: dict[str, Any] = {}
        for field, value in data.items():
            if value is None:
                continue
            if isinstance(value, bool):
                if value:
                    cleaned[field] = True
                continue
            if isinstance(value, str):
                text = value.strip()
                if not text:
                    continue
                cleaned[field] = text
                continue
            if field == "secondary_interests" and isinstance(value, list):
                items = [item.strip() for item in value if item and item.strip()]
                if items:
                    cleaned[field] = items
                continue
            cleaned[field] = value

        return ContactCardPatch.model_validate(cleaned)


def _clamp_confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))
