"""Verificação de webhook exigida pela Meta."""

from __future__ import annotations


class WebhookChallengeError(ValueError):
    """Erro de verificação do desafio do webhook."""


def verify_webhook_challenge(
    hub_mode: str | None,
    hub_verify_token: str | None,
    hub_challenge: str | None,
    expected_token: str | None,
) -> str:
    """Valida challenge de webhook e retorna o conteúdo a ser respondido.

    Args:
        hub_mode: Valor de hub.mode
        hub_verify_token: Valor de hub.verify_token
        hub_challenge: Valor de hub.challenge
        expected_token: Token configurado no servidor

    Raises:
        WebhookChallengeError: Se token estiver ausente ou inválido

    Returns:
        Desafio (string) ou vazio
    """
    if not expected_token:
        raise WebhookChallengeError("missing_verify_token")

    if hub_mode != "subscribe" or hub_verify_token != expected_token:
        raise WebhookChallengeError("verification_failed")

    return hub_challenge or ""
