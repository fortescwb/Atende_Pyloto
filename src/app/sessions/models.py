"""Modelo de sessão para atendimento.

Define a estrutura imutável de uma sessão de atendimento,
com estado FSM, histórico e contexto institucional.

Referência: FUNCIONAMENTO.md § 2 — Sessão e contexto
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from fsm.states import DEFAULT_INITIAL_STATE, SessionState


@dataclass(frozen=True, slots=True)
class SessionContext:
    """Contexto institucional mínimo de uma sessão.

    Atributos:
        tenant_id: Identificador do tenant/loja
        vertente: Vertente de atendimento (ex: vendas, suporte)
        rules: Regras específicas da sessão
        limits: Limites aplicados (timeout, mensagens, etc.)
    """

    tenant_id: str = ""
    vertente: str = "geral"
    rules: dict[str, Any] = field(default_factory=dict)
    limits: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class Session:
    """Sessão de atendimento.

    Mantém estado FSM, histórico e contexto institucional.
    Mutável apenas via métodos controlados para rastreabilidade.

    Atributos:
        session_id: Identificador único da sessão
        sender_id: Identificador do remetente (hash, não PII)
        current_state: Estado atual da FSM
        context: Contexto institucional
        history: Histórico de mensagens (sanitizado)
        turn_count: Número de turnos na sessão
        created_at: Timestamp de criação
        updated_at: Timestamp da última atualização
        expires_at: Timestamp de expiração
    """

    session_id: str
    sender_id: str
    current_state: SessionState = DEFAULT_INITIAL_STATE
    context: SessionContext = field(default_factory=SessionContext)
    history: list[str] = field(default_factory=list)
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

    def add_to_history(self, message: str, max_history: int = 10) -> None:
        """Adiciona mensagem ao histórico (FIFO com limite).

        Args:
            message: Mensagem sanitizada (sem PII)
            max_history: Limite máximo de mensagens no histórico
        """
        self.history.append(message)
        if len(self.history) > max_history:
            self.history = self.history[-max_history:]
        self.updated_at = datetime.now(UTC)

    def transition_to(self, new_state: SessionState) -> None:
        """Transita para novo estado.

        Args:
            new_state: Novo estado da FSM
        """
        self.current_state = new_state
        self.turn_count += 1
        self.updated_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Serializa sessão para persistência (sem PII).

        Returns:
            Dict serializável para JSON/Redis
        """
        return {
            "session_id": self.session_id,
            "sender_id": self.sender_id,
            "current_state": self.current_state.name,
            "context": {
                "tenant_id": self.context.tenant_id,
                "vertente": self.context.vertente,
                "rules": self.context.rules,
                "limits": self.context.limits,
            },
            "history": self.history,
            "turn_count": self.turn_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        """Deserializa sessão de persistência.

        Args:
            data: Dict serializado

        Returns:
            Instância de Session
        """
        from fsm.states import SessionState

        context_data = data.get("context", {})
        return cls(
            session_id=data["session_id"],
            sender_id=data["sender_id"],
            current_state=SessionState[data.get("current_state", "ENTRY")],
            context=SessionContext(
                tenant_id=context_data.get("tenant_id", ""),
                vertente=context_data.get("vertente", "geral"),
                rules=context_data.get("rules", {}),
                limits=context_data.get("limits", {}),
            ),
            history=data.get("history", []),
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
