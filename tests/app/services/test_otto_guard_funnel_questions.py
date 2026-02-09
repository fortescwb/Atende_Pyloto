"""Testa integração do build_next_step_cta para disparo de template/flow WhatsApp."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.domain.contact_card import ContactCard
from app.services.otto_guard_funnel_questions import build_next_step_cta

@pytest.mark.asyncio
async def test_build_next_step_cta_triggers_template_flow(monkeypatch):
    # Mock do outbound_sender
    class DummySender:
        async def send(self, request, payload):
            self.last_request = request
            return type("Resp", (), {"success": True})()
    sender = DummySender()

    card = ContactCard(
        wa_id="551199999999",
        phone="551199999999",
        whatsapp_name="Teste",
        primary_interest="saas",
        modules_needed=["crm"],
        users_count=5,
        specific_need="Preciso de CRM",
    )
    # ready_to_schedule_meeting deve ser True
    result = await build_next_step_cta(card, outbound_sender=sender)
    assert "Enviei um link" in result
    assert hasattr(sender, "last_request")
    req = sender.last_request
    assert req.template_name == "agendamento_reuniao"
    assert req.language == "pt_BR"
    assert req.category == "MARKETING"
    assert req.flow_id == "agendamento_reuniao"
    assert req.to == card.wa_id

@pytest.mark.asyncio
async def test_build_next_step_cta_error(monkeypatch):
    # outbound_sender ausente
    card = ContactCard(
        wa_id="551199999999",
        phone="551199999999",
        whatsapp_name="Teste",
        primary_interest="saas",
        modules_needed=["crm"],
        users_count=5,
        specific_need="Preciso de CRM",
    )
    result = await build_next_step_cta(card, outbound_sender=None)
    assert "erro" in result.lower() or "falha" in result.lower()
