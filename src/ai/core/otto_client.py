"""Protocolo para cliente do OttoAgent."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ai.models.otto import OttoDecision


class OttoClientProtocol(Protocol):
    """Contrato para clientes LLM do OttoAgent."""

    async def decide(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> OttoDecision | None:
        """Executa decisao do Otto e retorna structured output ou None."""
        ...
