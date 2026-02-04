"""Idempotência inbound para eventos de webhook."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_inbound_event_id(payload: dict[str, Any], raw_body: bytes) -> str:
    """Gera chave idempotente baseada no message_id ou hash do payload.

    Args:
        payload: Payload do webhook
        raw_body: Corpo bruto do request

    Returns:
        Identificador estável do evento inbound
    """
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", []) or []
            if messages and isinstance(messages[0], dict):
                msg_id = messages[0].get("id")
                if msg_id:
                    return msg_id

    digest = hashlib.sha256(
        raw_body or json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return f"payload:{digest}"
