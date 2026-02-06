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
from ai.utils.contact_card_extraction import (
    BOOL_FIELDS_ALLOW_FALSE,
    INT_FIELDS,
    PRIMARY_INTEREST_ALIASES,
    normalize_string_list,
    normalize_tools,
    parse_bool_value,
    parse_int_value,
)

logger = logging.getLogger(__name__)

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
            assistant_last_message=request.assistant_last_message,
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

        extracted_fields = list(patch.model_dump(exclude_none=True).keys())
        logger.info(
            "contact_card_extracted",
            extra={
                "fields_count": len(extracted_fields),
                "extracted_fields": extracted_fields,
                "confidence": confidence,
                "correlation_id": request.correlation_id,
            },
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
            if field in INT_FIELDS:
                parsed = parse_int_value(value)
                if parsed is not None:
                    normalized[field] = parsed
                continue
            if field == "has_crm":
                parsed_bool = parse_bool_value(value)
                if parsed_bool is not None:
                    normalized[field] = parsed_bool
                continue
            if field == "secondary_interests":
                items = normalize_string_list(value)
                if items:
                    normalized[field] = items
                continue
            if field == "current_tools":
                tools = normalize_tools(value)
                if tools:
                    normalized[field] = tools
                continue
            if isinstance(value, bool):
                if field in BOOL_FIELDS_ALLOW_FALSE:
                    normalized[field] = value
                elif value:
                    normalized[field] = True
                continue
            if isinstance(value, str):
                cleaned = value.strip()
                if not cleaned:
                    continue
                if field in {"primary_interest", "urgency", "company_size"}:
                    cleaned = cleaned.lower().replace(" ", "_").replace("-", "_")
                    if field == "primary_interest":
                        cleaned = PRIMARY_INTEREST_ALIASES.get(cleaned, cleaned)
                if field == "email":
                    cleaned = cleaned.lower()
                normalized[field] = cleaned
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
                if field in BOOL_FIELDS_ALLOW_FALSE:
                    cleaned[field] = value
                elif value:
                    cleaned[field] = True
                continue
            if isinstance(value, str):
                text = value.strip()
                if not text:
                    continue
                cleaned[field] = text
                continue
            if field == "secondary_interests":
                items = normalize_string_list(value)
                if items:
                    cleaned[field] = items
                continue
            if field == "current_tools":
                tools = normalize_tools(value)
                if tools:
                    cleaned[field] = tools
                continue
            cleaned[field] = value

        return ContactCardPatch.model_validate(cleaned)


def _clamp_confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))
