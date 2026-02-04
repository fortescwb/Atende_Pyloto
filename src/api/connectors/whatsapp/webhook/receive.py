"""Parse e validação inicial do webhook (sem PII)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ..signature import SignatureResult, verify_meta_signature

if TYPE_CHECKING:
    from collections.abc import Mapping


class WebhookRequestError(ValueError):
    """Erro base para falhas de webhook."""


class InvalidSignatureError(WebhookRequestError):
    """Assinatura inválida do webhook."""


class InvalidJsonError(WebhookRequestError):
    """JSON inválido no payload do webhook."""


def parse_webhook_request(
    raw_body: bytes,
    headers: Mapping[str, str],
    secret: str | None,
) -> tuple[dict[str, object], SignatureResult]:
    """Valida assinatura e parseia JSON do webhook.

    Args:
        raw_body: Corpo bruto do request
        headers: Headers recebidos
        secret: Secret do webhook

    Raises:
        InvalidSignatureError: Se assinatura for inválida
        InvalidJsonError: Se o JSON estiver inválido ou não for objeto

    Returns:
        (payload dict, SignatureResult)
    """
    signature_result = verify_meta_signature(raw_body, headers, secret)
    if not signature_result.valid:
        reason = signature_result.error or "invalid_signature"
        raise InvalidSignatureError(reason)

    try:
        payload = json.loads(raw_body or b"{}")
    except json.JSONDecodeError as exc:
        raise InvalidJsonError("invalid_json") from exc

    if not isinstance(payload, dict):
        raise InvalidJsonError("payload_not_object")

    return payload, signature_result
