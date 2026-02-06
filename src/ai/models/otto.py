"""Contratos do OttoAgent (agente principal)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

StateName = Literal[
    "INITIAL",
    "TRIAGE",
    "COLLECTING_INFO",
    "GENERATING_RESPONSE",
    "HANDOFF_HUMAN",
    "SELF_SERVE_INFO",
    "SCHEDULED_FOLLOWUP",
    "ROUTE_EXTERNAL",
    "TIMEOUT",
    "ERROR",
]

MessageType = Literal["text", "interactive_button", "interactive_list"]


class OttoRequest(BaseModel):
    """Request do OttoAgent."""

    model_config = ConfigDict(extra="ignore")

    user_message: str
    session_state: str
    correlation_id: str | None = None
    history: list[str] = Field(default_factory=list)
    contact_card_summary: str = ""
    contact_card_signals: dict[str, str] = Field(default_factory=dict)
    tenant_intent: str | None = None
    intent_confidence: float = 0.0
    loaded_contexts: list[str] = Field(default_factory=list)
    valid_transitions: list[str] = Field(default_factory=list)


class OttoDecision(BaseModel):
    """Decisao do OttoAgent (structured output)."""

    model_config = ConfigDict(extra="ignore")

    next_state: StateName
    response_text: str
    message_type: MessageType
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_human: bool = False
    reasoning_debug: str | None = None
