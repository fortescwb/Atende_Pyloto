"""Protocolo para cliente de extração de ContactCard."""

from __future__ import annotations

from typing import Any, Protocol


class ContactCardExtractorClientProtocol(Protocol):
    """Contrato para clientes LLM de extração de ContactCard."""

    async def extract(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any] | None:
        """Executa extração e retorna JSON (dict) ou None em caso de falha."""
        ...
