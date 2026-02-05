"""Protocolo para o Decisor Mestre (MasterDecider).

Define o contrato usado pelos casos de uso (use cases) para tomada de decisão.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class MasterDecision:
    """Representa a decisão do MasterDecider que o use case consome."""

    final_state: str
    should_close_session: bool
    final_text: str = ""
    final_message_type: str = "text"
    understood: bool = True
    close_reason: str | None = None
    audit_record: dict | None = None
    requires_human_escalation: bool = False
    confidence: float = 0.0


class MasterDeciderProtocol(Protocol):
    def decide(
        self,
        *,
        session: Any,
        ai_result: Any,
        fsm_result: Any,
        user_input: str,
    ) -> MasterDecision:
        ...
