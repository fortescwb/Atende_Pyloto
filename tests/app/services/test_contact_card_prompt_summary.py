"""Testes do resumo de ContactCard usado no prompt do Otto."""

from __future__ import annotations

from app.domain.contact_card import ContactCard


def _card(**overrides):
    base = {
        "wa_id": "5544999999999",
        "phone": "5544999999999",
        "whatsapp_name": "Cliente",
    }
    base.update(overrides)
    return ContactCard(**base)


def test_prompt_summary_includes_pending_crm_fields_when_incomplete() -> None:
    summary = _card().to_prompt_summary()
    lowered = summary.lower()

    assert "pendencias crm:" in lowered
    assert "interesse principal" in lowered
    assert "volume/dia" in lowered


def test_prompt_summary_hides_pending_crm_fields_when_key_data_exists() -> None:
    summary = _card(
        full_name="Joao",
        company="Empresa X",
        primary_interest="automacao_atendimento",
        specific_need="reduzir tempo de atendimento",
        has_crm=True,
        message_volume_per_day=120,
        urgency="high",
        budget_indication="ate 2k",
    ).to_prompt_summary()

    assert "Pendencias CRM:" not in summary
