"""Testes para respostas fixas de WhatsApp (quebra-gelos e comandos)."""

from __future__ import annotations

from app.services.whatsapp_fixed_replies import match_fixed_reply


def test_match_command_simple() -> None:
    result = match_fixed_reply("/automacao")
    assert result is not None
    assert result.kind == "command"
    assert result.prompt_vertical == "automacao_atendimento"
    assert "Otto, assistente virtual da Pyloto" in result.response_text


def test_match_command_with_suffix() -> None:
    result = match_fixed_reply("/automacao quero saber mais")
    assert result is not None
    assert result.kind == "command"


def test_match_command_with_underscore() -> None:
    result = match_fixed_reply("/entregas_servicos")
    assert result is not None
    assert result.kind == "command"


def test_match_quick_reply_with_accents() -> None:
    result = match_fixed_reply("Como funciona a Gestão de perfis e Tráfego?")
    assert result is not None
    assert result.kind == "quick_reply"
    assert result.prompt_vertical == "gestao_perfis_trafego"
    assert "Otto, assistente virtual da Pyloto" in result.response_text


def test_match_unknown_returns_none() -> None:
    assert match_fixed_reply("isso nao existe") is None
