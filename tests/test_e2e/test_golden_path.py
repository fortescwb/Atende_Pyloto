"""Teste E2E do golden path do inbound WhatsApp."""

from __future__ import annotations

from typing import Any

import pytest

from ai.models.contact_card_extraction import ContactCardExtractionResult, ContactCardPatch
from ai.models.otto import OttoDecision, OttoRequest
from app.bootstrap.whatsapp_adapters import GraphApiNormalizer
from app.infra.stores.contact_card_store import MemoryContactCardStore
from app.infra.stores.memory_stores import MemoryDedupeStore, MemorySessionStore
from app.protocols.models import OutboundMessageRequest, OutboundMessageResponse
from app.sessions.manager import SessionManager
from app.use_cases.whatsapp.process_inbound_canonical import ProcessInboundCanonicalUseCase


def _create_whatsapp_payload(
    *,
    message_id: str,
    from_number: str,
    text: str,
    whatsapp_name: str = "Lead Teste",
) -> dict[str, Any]:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "contacts": [{"profile": {"name": whatsapp_name}}],
                            "messages": [
                                {
                                    "id": message_id,
                                    "from": from_number,
                                    "timestamp": "1700000000",
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }


class _GoldenPathOttoAgent:
    async def decide(self, request: OttoRequest) -> OttoDecision:
        text = request.user_message.lower()
        if "saas" in text:
            return OttoDecision(
                next_state="COLLECTING_INFO",
                response_text="Perfeito. Para avancarmos, pode me informar seu e-mail?",
                message_type="text",
                confidence=0.95,
                requires_human=False,
            )
        return OttoDecision(
            next_state="TRIAGE",
            response_text="Ola! Posso te ajudar com SaaS, automacao ou sob medida.",
            message_type="text",
            confidence=0.95,
            requires_human=False,
        )


class _GoldenPathExtractor:
    async def extract(self, request: Any) -> ContactCardExtractionResult:
        text = request.user_message.lower()
        if "saas" not in text:
            return ContactCardExtractionResult.empty()
        return ContactCardExtractionResult(
            updates=ContactCardPatch(
                primary_interest="saas",
                email="lead@empresa.com",
            ),
            confidence=0.9,
        )


class _CapturingSender:
    def __init__(self) -> None:
        self.requests: list[OutboundMessageRequest] = []
        self.payloads: list[dict[str, Any]] = []

    async def send(
        self,
        request: OutboundMessageRequest,
        payload: dict[str, Any],
    ) -> OutboundMessageResponse:
        self.requests.append(request)
        self.payloads.append(payload)
        return OutboundMessageResponse(success=True, message_id=f"wamid.{len(self.payloads)}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_conversation_saas_interest() -> None:
    normalizer = GraphApiNormalizer()
    session_store = MemorySessionStore()
    session_manager = SessionManager(store=session_store)
    dedupe = MemoryDedupeStore()
    contact_card_store = MemoryContactCardStore()
    outbound_sender = _CapturingSender()

    use_case = ProcessInboundCanonicalUseCase(
        normalizer=normalizer,
        session_manager=session_manager,
        dedupe=dedupe,
        otto_agent=_GoldenPathOttoAgent(),
        outbound_sender=outbound_sender,
        contact_card_store=contact_card_store,
        contact_card_extractor=_GoldenPathExtractor(),
    )

    first_payload = _create_whatsapp_payload(
        message_id="msg-001",
        from_number="5544988887777",
        text="Ola",
    )
    first_result = await use_case.execute(
        payload=first_payload,
        correlation_id="corr-golden-1",
        tenant_id="pyloto",
    )

    assert first_result.processed == 1
    assert first_result.sent == 1
    assert first_result.skipped == 0
    assert first_result.final_state == "TRIAGE"

    second_payload = _create_whatsapp_payload(
        message_id="msg-002",
        from_number="5544988887777",
        text="Quero saber sobre o SaaS da Pyloto. Meu e-mail e lead@empresa.com",
    )
    second_result = await use_case.execute(
        payload=second_payload,
        correlation_id="corr-golden-2",
        tenant_id="pyloto",
    )

    assert second_result.processed == 1
    assert second_result.sent == 1
    assert second_result.skipped == 0
    assert second_result.final_state == "COLLECTING_INFO"

    session = await session_manager.resolve_or_create(
        sender_id="5544988887777",
        tenant_id="pyloto",
        whatsapp_name="Lead Teste",
    )
    assert session.current_state.name == "COLLECTING_INFO"
    assert len(session.history) >= 4

    contact_card = await contact_card_store.get("5544988887777")
    assert contact_card is not None
    assert contact_card.primary_interest == "saas"
    assert contact_card.email == "lead@empresa.com"

    assert len(outbound_sender.requests) == 2
    assert len(outbound_sender.payloads) == 2
    assert outbound_sender.requests[0].to == "+5544988887777"
    assert outbound_sender.requests[1].to == "+5544988887777"
