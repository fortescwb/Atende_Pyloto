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
    STRING_LIST_FIELDS,
    normalize_list_items,
    normalize_meeting_mode,
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
        raw = await self._client.extract(
            system_prompt=CONTACT_CARD_EXTRACTOR_SYSTEM,
            user_prompt=format_contact_card_extractor_prompt(
                user_message=request.user_message,
                assistant_last_message=request.assistant_last_message,
            ),
        )
        if raw is None:
            return ContactCardExtractionResult.empty()

        patch = self._parse_patch(raw, request.correlation_id)
        if patch is None:
            return ContactCardExtractionResult.empty()
        confidence = _clamp_confidence(raw.get("confidence", 0.0) if isinstance(raw, dict) else 0.0)
        evidence = _extract_evidence(raw)
        self._log_extracted_patch(patch, confidence, request.correlation_id)
        return ContactCardExtractionResult(updates=patch, confidence=confidence, evidence=evidence)

    def _parse_patch(
        self,
        raw: dict[str, Any] | Any,
        correlation_id: str | None,
    ) -> ContactCardPatch | None:
        updates_raw = raw.get("updates") if isinstance(raw, dict) else {}
        updates_raw = self._normalize_raw_updates(updates_raw)
        try:
            return ContactCardPatch.model_validate(updates_raw)
        except ValidationError:
            logger.warning(
                "contact_card_patch_invalid",
                extra={
                    "component": "contact_card_extractor",
                    "action": "validate_patch",
                    "result": "invalid",
                    "correlation_id": correlation_id,
                },
            )
            return None

    def _log_extracted_patch(
        self,
        patch: ContactCardPatch,
        confidence: float,
        correlation_id: str | None,
    ) -> None:
        extracted_fields = list(patch.model_dump(exclude_none=True).keys())
        logger.info(
            "contact_card_extracted",
            extra={
                "component": "contact_card_extractor",
                "action": "extract",
                "result": "ok",
                "fields_count": len(extracted_fields),
                "extracted_fields": extracted_fields,
                "confidence": confidence,
                "correlation_id": correlation_id,
            },
        )

    @staticmethod
    def _normalize_raw_updates(raw_updates: Any) -> dict[str, Any]:
        if not isinstance(raw_updates, dict):
            return {}
        normalized: dict[str, Any] = {}
        for field, value in raw_updates.items():
            normalized_value = _normalize_patch_field(field, value)
            if normalized_value is not None:
                normalized[field] = normalized_value
        return normalized


def _normalize_patch_field(field: str, value: Any) -> Any | None:
    if value is None:
        return None
    if field in INT_FIELDS:
        return parse_int_value(value)
    if field in BOOL_FIELDS_ALLOW_FALSE:
        return parse_bool_value(value)
    if field == "secondary_interests":
        return _non_empty(normalize_string_list(value))
    if field == "current_tools":
        return _non_empty(normalize_tools(value))
    if field in STRING_LIST_FIELDS:
        return _non_empty(normalize_list_items(field, normalize_string_list(value)))
    if isinstance(value, bool):
        return _normalize_bool_field(field, value)
    if isinstance(value, str):
        return _normalize_string_field(field, value)
    return value


def _normalize_bool_field(field: str, value: bool) -> bool | None:
    if field in BOOL_FIELDS_ALLOW_FALSE:
        return value
    return True if value else None


def _normalize_string_field(field: str, value: str) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    if field in {"primary_interest", "urgency", "company_size", "meeting_mode"}:
        cleaned = cleaned.lower().replace(" ", "_").replace("-", "_")
        if field == "primary_interest":
            cleaned = PRIMARY_INTEREST_ALIASES.get(cleaned, cleaned)
        if field == "meeting_mode":
            cleaned = normalize_meeting_mode(cleaned)
    if field == "email":
        return cleaned.lower()
    return cleaned


def _non_empty(items: list[str]) -> list[str] | None:
    return items if items else None


def _extract_evidence(raw: Any) -> list[str]:
    if isinstance(raw, dict) and isinstance(raw.get("evidence"), list):
        return raw.get("evidence", [])
    return []


def _clamp_confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))
