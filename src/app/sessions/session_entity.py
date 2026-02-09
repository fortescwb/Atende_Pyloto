"""Entidade de sessão de atendimento."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.domain.contact_card import ContactCard
from app.sessions.history import HistoryEntry, HistoryRole
from app.sessions.session_context import SessionContext
from fsm.states import DEFAULT_INITIAL_STATE, SessionState

_LEGACY_STATE_BY_INT: dict[int, SessionState] = {
    1: SessionState.INITIAL,
    2: SessionState.TRIAGE,
    3: SessionState.COLLECTING_INFO,
    4: SessionState.GENERATING_RESPONSE,
    5: SessionState.HANDOFF_HUMAN,
    6: SessionState.SELF_SERVE_INFO,
    7: SessionState.ROUTE_EXTERNAL,
    8: SessionState.SCHEDULED_FOLLOWUP,
    9: SessionState.TIMEOUT,
    10: SessionState.ERROR,
}


def _parse_session_state(value: Any) -> SessionState:
    """Normaliza estado serializado com fallback seguro."""
    if isinstance(value, SessionState):
        return value
    if isinstance(value, int):
        return _LEGACY_STATE_BY_INT.get(value, DEFAULT_INITIAL_STATE)
    if isinstance(value, str):
        if value == "ENTRY":
            return DEFAULT_INITIAL_STATE
        state = SessionState.__members__.get(value)
        if state is not None:
            return state
    return DEFAULT_INITIAL_STATE


@dataclass(slots=True)
class Session:
    """Sessão de atendimento."""

    session_id: str
    sender_id: str
    current_state: SessionState = DEFAULT_INITIAL_STATE
    context: SessionContext = field(default_factory=SessionContext)
    history: list[HistoryEntry] = field(default_factory=list)
    contact_card: ContactCard | None = None
    turn_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None

    @property
    def is_expired(self) -> bool:
        """Verifica se a sessão expirou."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    @property
    def is_terminal(self) -> bool:
        """Verifica se está em estado terminal."""
        from fsm.states import is_terminal

        return is_terminal(self.current_state)

    @property
    def history_as_strings(self) -> list[str]:
        """Retorna histórico como lista de strings (backwards compat)."""
        return [str(entry) for entry in self.history]

    def add_to_history(
        self,
        content: str,
        role: HistoryRole = HistoryRole.USER,
        detected_intent: str | None = None,
        max_history: int | None = 10,
    ) -> None:
        """Adiciona mensagem ao histórico (FIFO com limite)."""
        entry = HistoryEntry(
            role=role,
            content=content,
            detected_intent=detected_intent,
        )
        self.history.append(entry)
        if max_history is not None and max_history > 0 and len(self.history) > max_history:
            self.history = self.history[-max_history:]
        self.updated_at = datetime.now(UTC)

    def transition_to(self, new_state: SessionState) -> None:
        """Transita para novo estado."""
        self.current_state = new_state
        self.turn_count += 1
        self.updated_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Serializa sessão para persistência (sem PII)."""
        return {
            "session_id": self.session_id,
            "sender_id": self.sender_id,
            "current_state": self.current_state.name,
            "context": {
                "tenant_id": self.context.tenant_id,
                "vertente": self.context.vertente,
                "rules": self.context.rules,
                "limits": self.context.limits,
                "prompt_vertical": self.context.prompt_vertical,
                "prompt_contexts": list(self.context.prompt_contexts),
            },
            "history": [entry.to_dict() for entry in self.history],
            "contact_card": (
                self.contact_card.model_dump(mode="json", exclude_none=True)
                if self.contact_card
                else {}
            ),
            "turn_count": self.turn_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        """Deserializa sessão de persistência."""
        context_data = data.get("context", {})
        raw_history = data.get("history", [])
        history: list[HistoryEntry] = []
        for item in raw_history:
            if isinstance(item, str):
                history.append(HistoryEntry(role=HistoryRole.USER, content=item))
            elif isinstance(item, dict):
                history.append(HistoryEntry.from_dict(item))

        contact_data = data.get("contact_card") or data.get("lead_profile") or {}
        contact_card: ContactCard | None = None
        if contact_data:
            try:
                contact_card = ContactCard.from_firestore_dict(contact_data)
            except Exception:
                contact_card = None

        return cls(
            session_id=data["session_id"],
            sender_id=data["sender_id"],
            current_state=_parse_session_state(data.get("current_state")),
            context=SessionContext(
                tenant_id=context_data.get("tenant_id", ""),
                vertente=context_data.get("vertente", "geral"),
                rules=context_data.get("rules", {}),
                limits=context_data.get("limits", {}),
                prompt_vertical=context_data.get("prompt_vertical", ""),
                prompt_contexts=context_data.get("prompt_contexts", []) or [],
            ),
            history=history,
            contact_card=contact_card,
            turn_count=data.get("turn_count", 0),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now(UTC)
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if "updated_at" in data
                else datetime.now(UTC)
            ),
            expires_at=(
                datetime.fromisoformat(data["expires_at"])
                if data.get("expires_at")
                else None
            ),
        )
