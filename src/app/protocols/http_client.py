"""Protocolos HTTP usados pelo app.

Evita dependência direta da camada api.
"""

from __future__ import annotations

from typing import Any, Protocol


class WhatsAppHttpClientProtocol(Protocol):
    """Contrato mínimo para cliente HTTP do WhatsApp."""

    async def send_message(
        self,
        endpoint: str,
        access_token: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]: ...
