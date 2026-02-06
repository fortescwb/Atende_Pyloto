"""Testes para ContactCardExtractorService."""

from __future__ import annotations

import pytest

from ai.models.contact_card_extraction import ContactCardExtractionRequest
from ai.services.contact_card_extractor import ContactCardExtractorService


class FakeClient:
    """Fake client para simular respostas do LLM."""

    def __init__(self, payload):
        self._payload = payload

    async def extract(self, *, system_prompt: str, user_prompt: str):
        return self._payload


@pytest.mark.asyncio
async def test_no_updates_returns_empty_patch() -> None:
    service = ContactCardExtractorService(FakeClient({"updates": {}, "confidence": 0.9}))
    result = await service.extract(
        ContactCardExtractionRequest(
            user_message="Oi",
        )
    )
    assert result.has_updates is False
    assert result.confidence == 0.9


@pytest.mark.asyncio
async def test_email_is_normalized_to_lowercase() -> None:
    service = ContactCardExtractorService(
        FakeClient({"updates": {"email": "User@Example.com"}, "confidence": 0.7})
    )
    result = await service.extract(
        ContactCardExtractionRequest(
            user_message="Meu email e User@Example.com",
        )
    )
    assert result.updates.email == "user@example.com"


@pytest.mark.asyncio
async def test_full_name_is_kept() -> None:
    service = ContactCardExtractorService(
        FakeClient({"updates": {"full_name": "Joao Silva"}, "confidence": 0.8})
    )
    result = await service.extract(
        ContactCardExtractionRequest(
            user_message="Sou Joao Silva",
        )
    )
    assert result.updates.full_name == "Joao Silva"


@pytest.mark.asyncio
async def test_primary_interest() -> None:
    service = ContactCardExtractorService(
        FakeClient({"updates": {"primary_interest": "saas"}, "confidence": 0.6})
    )
    result = await service.extract(
        ContactCardExtractionRequest(
            user_message="Quero um SaaS",
        )
    )
    assert result.updates.primary_interest == "saas"


@pytest.mark.asyncio
async def test_multiple_secondary_interests() -> None:
    service = ContactCardExtractorService(
        FakeClient(
            {
                "updates": {"secondary_interests": ["sob_medida", "automacao_atendimento"]},
                "confidence": 0.75,
            }
        )
    )
    result = await service.extract(
        ContactCardExtractionRequest(
            user_message="Preciso de sob medida e automacao",
        )
    )
    assert result.updates.secondary_interests == ["sob_medida", "automacao_atendimento"]
