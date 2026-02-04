"""Protocolos de domínio para Conversation Store.

Define contratos para persistência permanente de conversas.
Usado para dual-write: Redis (sessão) + Firestore (permanente).

Referência: TODO_llm.md § 2.2 — Fluxo de Persistência
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime  # noqa: TC003 - usado em runtime nos dataclasses
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    """Mensagem individual de uma conversa.

    Representa uma mensagem persistida (user ou assistant),
    com metadados para recuperação e análise.
    """

    message_id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    channel: str = "whatsapp"
    detected_intent: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LeadData:
    """Dados do lead persistidos.

    Perfil do lead coletado durante as conversas,
    sem PII sensível (telefone é hash).
    """

    phone_hash: str
    name: str = ""
    email: str = ""
    first_contact: datetime | None = None
    last_contact: datetime | None = None
    primary_intent: str = ""
    total_messages: int = 0
    tenant_id: str = "default"
    channel: str = "whatsapp"
    metadata: dict[str, str] = field(default_factory=dict)


class ConversationStoreProtocol(ABC):
    """Contrato para armazenamento permanente de conversas.

    Responsabilidades:
        - Persistir mensagens de forma append-only
        - Recuperar histórico de conversas por lead
        - Manter dados do lead atualizados
        - Suportar queries por tenant/canal

    Invariantes:
        - Sem PII em logs
        - Idempotência por message_id
        - TTL configurável (LGPD)
    """

    @abstractmethod
    async def append_message(
        self,
        phone_hash: str,
        message: ConversationMessage,
        *,
        tenant_id: str = "default",
    ) -> None:
        """Persiste uma mensagem de conversa.

        Args:
            phone_hash: Hash do telefone (sem PII)
            message: Mensagem a persistir
            tenant_id: ID do tenant

        Raises:
            ConversationStoreError: Erro de persistência
        """

    @abstractmethod
    async def get_messages(
        self,
        phone_hash: str,
        *,
        limit: int = 20,
        tenant_id: str = "default",
    ) -> Sequence[ConversationMessage]:
        """Recupera últimas mensagens de um lead.

        Args:
            phone_hash: Hash do telefone
            limit: Máximo de mensagens a retornar
            tenant_id: ID do tenant

        Returns:
            Lista de mensagens ordenadas por timestamp (mais antigas primeiro)
        """

    @abstractmethod
    async def upsert_lead(
        self,
        lead: LeadData,
    ) -> None:
        """Cria ou atualiza dados do lead.

        Args:
            lead: Dados do lead

        Raises:
            ConversationStoreError: Erro de persistência
        """

    @abstractmethod
    async def get_lead(
        self,
        phone_hash: str,
        *,
        tenant_id: str = "default",
    ) -> LeadData | None:
        """Recupera dados de um lead.

        Args:
            phone_hash: Hash do telefone
            tenant_id: ID do tenant

        Returns:
            Dados do lead ou None se não existir
        """


class ConversationStoreError(Exception):
    """Erro de persistência em ConversationStore."""
