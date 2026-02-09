"""Testes para merge de ContactCard com patch extraído."""

from __future__ import annotations

from ai.models.contact_card_extraction import ContactCardPatch
from app.domain.contact_card import ContactCard
from app.services.contact_card_merge import apply_contact_card_patch


def _new_contact_card() -> ContactCard:
    return ContactCard(
        wa_id="5541999999999",
        phone="5541999999999",
        whatsapp_name="Contato WhatsApp",
    )


def test_apply_patch_fills_empty_fields_and_recalculates_score() -> None:
    card = _new_contact_card()
    patch = ContactCardPatch(
        full_name="Ana Souza",
        email="ana@empresa.com",
        primary_interest="saas",
        specific_need="Automatizar atendimento",
    )

    updated = apply_contact_card_patch(card, patch)

    assert updated is True
    assert card.full_name == "Ana Souza"
    assert card.email == "ana@empresa.com"
    assert card.primary_interest == "saas"
    assert card.is_qualified is True
    assert card.qualification_score >= 60


def test_apply_patch_does_not_overwrite_existing_text_but_updates_urgency() -> None:
    card = _new_contact_card()
    card.full_name = "Nome Inicial"
    card.urgency = "low"

    patch = ContactCardPatch(full_name="Nome Novo", urgency="high")
    updated = apply_contact_card_patch(card, patch)

    assert updated is True
    assert card.full_name == "Nome Inicial"
    assert card.urgency == "high"


def test_apply_patch_merges_lists_with_limits_and_promotes_true_flags_only() -> None:
    card = _new_contact_card()
    card.secondary_interests = ["saas", "sob_medida"]
    card.modules_needed = [f"mod_{i}" for i in range(1, 12)]
    card.requested_human = True
    card.showed_objection = False

    patch = ContactCardPatch(
        secondary_interests=[
            "saas",
            "automacao_atendimento",
            "intermediacao_entregas",
            "extra",
        ],
        modules_needed=["mod_10", "mod_12", "mod_13"],
        requested_human=False,
        showed_objection=True,
    )

    updated = apply_contact_card_patch(card, patch)

    assert updated is True
    assert card.secondary_interests == [
        "saas",
        "sob_medida",
        "automacao_atendimento",
    ]
    assert len(card.modules_needed) == 12
    assert "mod_12" in card.modules_needed
    assert "mod_13" not in card.modules_needed
    assert card.requested_human is True
    assert card.showed_objection is True
