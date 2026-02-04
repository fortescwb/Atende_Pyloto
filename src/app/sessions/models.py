"""Modelo de sessão para atendimento.

Define a estrutura imutável de uma sessão de atendimento,
com estado FSM, histórico e contexto institucional.

Referência: FUNCIONAMENTO.md § 2 — Sessão e contexto
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from fsm.states import DEFAULT_INITIAL_STATE, SessionState


class HistoryRole(Enum):
    """Role da mensagem no histórico."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """Entrada estruturada do histórico de conversa.

    Atributos:
        role: Quem enviou a mensagem (user/assistant/system)
        content: Conteúdo da mensagem (sanitizado, sem PII)
        timestamp: Momento da mensagem
        detected_intent: Intenção detectada neste turno (opcional)
    """

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


@dataclass(slots=True)
class LeadProfile:
    """Perfil do lead coletado durante a conversa.

    Atributos:
        name: Nome do lead (quando coletado)
        email: Email do lead (quando coletado)
        phone: Telefone do lead (hash, não o número real)
        primary_intent: Intenção principal detectada
        collected_data: Dados adicionais coletados
        pending_questions: Perguntas pendentes a fazer
    """

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    primary_intent: str | None = None
    collected_data: dict[str, Any] = field(default_factory=dict)
    pending_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serializa para persistência."""
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "primary_intent": self.primary_intent,
            "collected_data": self.collected_data,
            "pending_questions": self.pending_questions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LeadProfile:
        """Deserializa de persistência."""
        return cls(
            name=data.get("name"),
            email=data.get("email"),
            phone=data.get("phone"),
            primary_intent=data.get("primary_intent"),
            collected_data=data.get("collected_data", {}),
            pending_questions=data.get("pending_questions", []),
        )

    def has_contact_info(self) -> bool:
        """Verifica se tem informação de contato."""
        return bool(self.email or self.phone)


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
        history: Histórico de mensagens estruturado
        lead_profile: Perfil do lead coletado
        turn_count: Número de turnos na sessão
        created_at: Timestamp de criação
        updated_at: Timestamp da última atualização
        expires_at: Timestamp de expiração
    """

    session_id: str
    sender_id: str
    current_state: SessionState = DEFAULT_INITIAL_STATE
    context: SessionContext = field(default_factory=SessionContext)
    history: list[HistoryEntry] = field(default_factory=list)
    lead_profile: LeadProfile = field(default_factory=LeadProfile)
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
        """Adiciona mensagem ao histórico (FIFO com limite).

        Args:
            content: Conteúdo da mensagem (sanitizado, sem PII)
            role: Quem enviou a mensagem
            detected_intent: Intenção detectada neste turno
            max_history: Limite máximo de mensagens no histórico
        """
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
            "history": [entry.to_dict() for entry in self.history],
            "lead_profile": self.lead_profile.to_dict(),
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

        Note:
            Suporta formato legado (history como list[str])
            e novo formato (history como list[HistoryEntry]).
        """
        from fsm.states import SessionState

        context_data = data.get("context", {})

        # Deserializa histórico com suporte a formato legado
        raw_history = data.get("history", [])
        history: list[HistoryEntry] = []
        for item in raw_history:
            if isinstance(item, str):
                # Formato legado: string simples
                history.append(HistoryEntry(role=HistoryRole.USER, content=item))
            elif isinstance(item, dict):
                # Novo formato: dict estruturado
                history.append(HistoryEntry.from_dict(item))

        # Deserializa lead profile
        lead_data = data.get("lead_profile", {})
        lead_profile = LeadProfile.from_dict(lead_data) if lead_data else LeadProfile()

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
            history=history,
            lead_profile=lead_profile,
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
