"""Validação de assinatura HMAC-SHA256 para webhooks."""

from __future__ import annotations

import hashlib
import hmac


def validate_flow_signature(payload: bytes, signature: str, secret: bytes) -> bool:
    """Valida assinatura HMAC-SHA256 do Meta.

    Args:
        payload: Corpo bruto da requisição
        signature: Header X-Hub-Signature-256
        secret: Secret do endpoint em bytes

    Returns:
        True se assinatura válida
    """
    if not signature.startswith("sha256="):
        return False

    expected = signature[7:]
    computed = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, expected)
