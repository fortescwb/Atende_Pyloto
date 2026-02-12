"""Testa integracao do build_next_step_cta para disparo de template/flow WhatsApp."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.appointment import TimeSlot
from app.domain.contact_card import ContactCard
from app.services.otto_guard_funnel_questions import build_next_step_cta


class DummySender:
    async def send(self, request, payload):
        self.last_request = request
        self.last_payload = payload
        return type("Resp", (), {"success": True})()


def _ready_card() -> ContactCard:
    return ContactCard(
        wa_id="551199999999",
        phone="551199999999",
        whatsapp_name="Teste",
        primary_interest="saas",
        modules_needed=["crm"],
        users_count=5,
        specific_need="Preciso de CRM",
    )


@pytest.mark.asyncio
async def test_build_next_step_cta_triggers_template_flow() -> None:
    sender = DummySender()

    result = await build_next_step_cta(_ready_card(), outbound_sender=sender)

    assert "Enviei um link" in result
    assert hasattr(sender, "last_request")
    req = sender.last_request
    assert req.template_name == "agendamento_reuniao"
    assert req.language == "pt_BR"
    assert req.category == "MARKETING"
    assert req.flow_id == "agendamento_reuniao"
    assert req.to == "551199999999"


@pytest.mark.asyncio
async def test_build_next_step_cta_error_when_sender_missing() -> None:
    result = await build_next_step_cta(_ready_card(), outbound_sender=None)

    assert "erro" in result.lower() or "falha" in result.lower()


@pytest.mark.asyncio
async def test_build_next_step_cta_returns_full_calendar_message() -> None:
    class FullCalendar:
        async def check_availability(self, date, *, start_hour=9, end_hour=17):
            start = datetime(2026, 2, 16, 10, 0, tzinfo=UTC)
            end = start + timedelta(minutes=30)
            return [TimeSlot(start=start, end=end, available=False)]

    sender = DummySender()

    result = await build_next_step_cta(
        _ready_card(),
        outbound_sender=sender,
        calendar_service=FullCalendar(),
    )

    assert "agenda cheia" in result
    assert not hasattr(sender, "last_request")


@pytest.mark.asyncio
async def test_build_next_step_cta_sends_when_calendar_has_slots() -> None:
    class AvailableCalendar:
        async def check_availability(self, date, *, start_hour=9, end_hour=17):
            start = datetime(2026, 2, 16, 10, 0, tzinfo=UTC)
            end = start + timedelta(minutes=30)
            return [TimeSlot(start=start, end=end, available=True)]

    sender = DummySender()

    result = await build_next_step_cta(
        _ready_card(),
        outbound_sender=sender,
        calendar_service=AvailableCalendar(),
    )

    assert "Enviei um link" in result
    assert hasattr(sender, "last_request")
