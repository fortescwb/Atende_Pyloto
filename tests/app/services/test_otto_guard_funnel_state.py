"""Testes para regras de qualificacao minima do funil."""

from __future__ import annotations

from app.domain.contact_card import ContactCard
from app.services.otto_guard_funnel_state import ready_to_schedule_meeting


def _contact_card(**kwargs) -> ContactCard:
    base = {
        "wa_id": "551199999999",
        "phone": "551199999999",
        "whatsapp_name": "Teste",
    }
    base.update(kwargs)
    return ContactCard(**base)


def test_ready_to_schedule_automacao_requires_three_signals() -> None:
    card = _contact_card(
        primary_interest="automacao_atendimento",
        specific_need="bot no WhatsApp",
        message_volume_per_day=200,
        attendants_count=2,
    )
    assert ready_to_schedule_meeting(card) is True

    incomplete = _contact_card(
        primary_interest="automacao_atendimento",
        message_volume_per_day=200,
    )
    assert ready_to_schedule_meeting(incomplete) is False


def test_ready_to_schedule_sob_medida_requires_two_signals() -> None:
    card = _contact_card(
        primary_interest="sob_medida",
        desired_features=["agenda", "crm"],
        integrations_needed=["erp"],
    )
    assert ready_to_schedule_meeting(card) is True

    incomplete = _contact_card(
        primary_interest="sob_medida",
        desired_features=["agenda"],
    )
    assert ready_to_schedule_meeting(incomplete) is False


def test_ready_to_schedule_saas_requires_modules_and_users() -> None:
    card = _contact_card(
        primary_interest="saas",
        modules_needed=["crm"],
        users_count=5,
    )
    assert ready_to_schedule_meeting(card) is True

    incomplete = _contact_card(
        primary_interest="saas",
        modules_needed=["crm"],
    )
    assert ready_to_schedule_meeting(incomplete) is False


def test_ready_to_schedule_trafego_requires_two_signals() -> None:
    card = _contact_card(
        primary_interest="gestao_perfis_trafego",
        specific_need="quero mais leads",
        budget_indication="R$ 3k",
    )
    assert ready_to_schedule_meeting(card) is True
