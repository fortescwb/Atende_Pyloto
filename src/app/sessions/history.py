"""Tipos de histórico da sessão."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class HistoryRole(Enum):
    """Role da mensagem no histórico."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """Entrada estruturada do histórico de conversa."""

    role: HistoryRole
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    detected_intent: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializa entrada para persistência."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "detected_intent": self.detected_intent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistoryEntry:
        """Deserializa entrada de persistência."""
        return cls(
            role=HistoryRole(data.get("role", "user")),
            content=data.get("content", ""),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if "timestamp" in data
                else datetime.now(UTC)
            ),
            detected_intent=data.get("detected_intent"),
        )

    def __str__(self) -> str:
        """Representação string para prompts (backwards compat)."""
        prefix = "Usuário" if self.role == HistoryRole.USER else "Otto"
        return f"{prefix}: {self.content}"
