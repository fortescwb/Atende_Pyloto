"""Modelos de coordenação para WhatsApp Flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class FlowResponse:
    """Resultado do envio de um Flow."""

    flow_id: str
    recipient_id: str
    message_id: str | None
    success: bool
    error_message: str | None = None


@dataclass(slots=True, frozen=True)
class DecryptedFlowData:
    """Dados descriptografados de um Flow recebido."""

    flow_token: str
    action: str
    screen: str
    data: dict[str, Any]
    version: str | None = None
