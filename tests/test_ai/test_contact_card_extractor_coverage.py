"""Cobertura adicional para ContactCardExtractorService."""

from __future__ import annotations

from typing import Any

import pytest

from ai.models.contact_card_extraction import ContactCardExtractionRequest
from ai.services.contact_card_extractor import (
    ContactCardExtractorService,
    _clamp_confidence,
    _extract_evidence,
    _normalize_bool_field,
    _normalize_patch_field,
    _normalize_string_field,
)


class _FakeClient:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    async def extract(self, *, system_prompt: str, user_prompt: str) -> Any:
        assert isinstance(system_prompt, str)
        assert isinstance(user_prompt, str)
        return self._payload


@pytest.mark.asyncio
async def test_extract_returns_empty_when_client_returns_none() -> None:
    service = ContactCardExtractorService(_FakeClient(None))

    result = await service.extract(
        ContactCardExtractionRequest(user_message="oi", correlation_id="corr-1")
    )

    assert result.has_updates is False
    assert result.confidence == 0.0
    assert result.evidence is None


@pytest.mark.asyncio
async def test_extract_returns_empty_when_patch_is_invalid(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = ContactCardExtractorService(
        _FakeClient(
            {
                "updates": {
                    # Tipo inválido para full_name (espera str | None).
                    "full_name": {"first": "Ada"},
                },
                "confidence": 0.9,
            }
        )
    )

    with caplog.at_level("WARNING"):
        result = await service.extract(
            ContactCardExtractionRequest(user_message="oi", correlation_id="corr-2")
        )

    assert result.has_updates is False
    assert result.confidence == 0.0
    assert "contact_card_patch_invalid" in caplog.text


@pytest.mark.asyncio
async def test_extract_clamps_confidence_and_keeps_evidence() -> None:
    service = ContactCardExtractorService(
        _FakeClient(
            {
                "updates": {
                    "primary_interest": "Automacao WhatsApp",
                    "meeting_mode": "presencial",
                    "email": "Lead@Empresa.COM",
                },
                "confidence": "2.5",
                "evidence": ["mensagem 1", "mensagem 2"],
            }
        )
    )

    result = await service.extract(
        ContactCardExtractionRequest(user_message="quero automacao", correlation_id="corr-3")
    )

    assert result.confidence == 1.0
    assert result.evidence == ["mensagem 1", "mensagem 2"]
    assert result.updates.primary_interest == "automacao_atendimento"
    assert result.updates.meeting_mode == "presencial"
    assert result.updates.email == "lead@empresa.com"


def test_normalize_raw_updates_returns_empty_for_non_dict() -> None:
    assert ContactCardExtractorService._normalize_raw_updates(["x"]) == {}
    assert ContactCardExtractorService._normalize_raw_updates("x") == {}


def test_normalize_patch_field_covers_scalar_and_list_branches() -> None:
    assert _normalize_patch_field("email", " Lead@Empresa.com ") == "lead@empresa.com"
    assert _normalize_patch_field("full_name", "   ") is None
    assert _normalize_patch_field("meeting_mode", "remote / zoom") == "online"
    assert _normalize_patch_field("primary_interest", "bot_whatsapp") == "automacao_atendimento"
    assert _normalize_patch_field("has_crm", False) is False
    assert _normalize_patch_field("requested_human", False) is None
    assert _normalize_patch_field("users_count", "120 usuarios") == 120
    assert _normalize_patch_field("modules_needed", ["CRM", "crm"]) == ["crm"]
    assert _normalize_patch_field("other_field", {"a": 1}) == {"a": 1}
    assert _normalize_patch_field("role", None) is None


def test_internal_helpers_cover_error_and_fallback_paths() -> None:
    assert _normalize_bool_field("requested_human", True) is True
    assert _normalize_bool_field("requested_human", False) is None
    assert _normalize_bool_field("has_crm", False) is False

    assert _normalize_string_field("meeting_mode", "") is None
    assert _normalize_string_field("primary_interest", "trafego-pago") == "gestao_perfis_trafego"
    assert _normalize_string_field("meeting_mode", "encontro local") == "presencial"
    assert _normalize_string_field("meeting_mode", "modo estranho") == "online"

    assert _extract_evidence({"evidence": ["x"]}) == ["x"]
    assert _extract_evidence({"evidence": "x"}) == []
    assert _extract_evidence(None) == []

    assert _clamp_confidence("0.7") == 0.7
    assert _clamp_confidence(-1) == 0.0
    assert _clamp_confidence(8) == 1.0
    assert _clamp_confidence("not-a-number") == 0.0
