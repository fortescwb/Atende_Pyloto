"""Gerenciador de sessões para atendimento.

Resolve, cria e atualiza sessões de atendimento.
Suporta dual-write (Redis + Firestore) para persistência permanente.

Referência: TODO_llm.md § 2.2 — Fluxo de Persistência
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.sessions.models import HistoryEntry, HistoryRole, LeadProfile, Session, SessionContext
from fsm.states import DEFAULT_INITIAL_STATE

if TYPE_CHECKING:
    from app.protocols.conversation_store import (
        ConversationStoreProtocol,
    )
    from app.protocols.session_store import AsyncSessionStoreProtocol

logger = logging.getLogger(__name__)

DEFAULT_SESSION_TTL_SECONDS = 7200
DEFAULT_HISTORY_RECOVERY_LIMIT = 20


class SessionManager:
    """Gerenciador de sessões de atendimento.

    Suporta dual-write pattern:
        - Redis: sessão ativa (TTL 2h)
        - Firestore: histórico permanente (opcional)

    Quando usuário retorna após sessão expirar, o histórico
    é recuperado do Firestore automaticamente.
    """

    __slots__ = ("_conversation_store", "_store", "_ttl_seconds")

    def __init__(
        self,
        store: AsyncSessionStoreProtocol,
        ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
        conversation_store: ConversationStoreProtocol | None = None,
    ) -> None:
        """Inicializa gerenciador.

        Args:
            store: Store de sessão (Redis)
            ttl_seconds: TTL da sessão em segundos
            conversation_store: Store de conversas permanente (Firestore, opcional)
        """
        self._store = store
        self._ttl_seconds = ttl_seconds
        self._conversation_store = conversation_store

    @staticmethod
    def _hash_sender(sender_id: str) -> str:
        """Gera hash do sender_id para uso como chave."""
        return hashlib.sha256(sender_id.encode()).hexdigest()[:16]

    def _generate_session_id(self, sender_hash: str) -> str:
        """Gera ID determinístico por remetente."""
        return f"sess_{sender_hash}"

    async def resolve_or_create(
        self,
        sender_id: str,
        tenant_id: str = "",
        vertente: str = "geral",
        channel: str = "whatsapp",
    ) -> Session:
        """Resolve sessão existente ou cria nova.

        Fluxo de recuperação:
            1. Busca sessão ativa no Redis
            2. Se não encontra, busca histórico no Firestore
            3. Reconstrói sessão com contexto do lead

        Args:
            sender_id: ID do remetente (telefone/username)
            tenant_id: ID do tenant
            vertente: Vertente de atendimento
            channel: Canal de origem

        Returns:
            Sessão existente ou nova
        """
        sender_hash = self._hash_sender(sender_id)
        session_id = self._generate_session_id(sender_hash)

        existing = await self._store.load_async(session_id)
        if existing is not None:
            session = existing if isinstance(existing, Session) else Session.from_dict(existing)
            if not session.is_expired and not session.is_terminal:
                logger.debug("session_resolved", extra={"session_id": session.session_id})
                return session

        # Sessão não encontrada no Redis, tentar recuperar do Firestore
        return await self._create_with_recovery(
            sender_hash, session_id, tenant_id, vertente, channel
        )

    async def _create_with_recovery(
        self,
        sender_hash: str,
        session_id: str,
        tenant_id: str,
        vertente: str,
        channel: str,
    ) -> Session:
        """Cria nova sessão com recuperação de histórico do Firestore.

        Se ConversationStore está configurado, tenta recuperar:
            - Perfil do lead (nome, email, intent)
            - Últimas N mensagens

        Args:
            sender_hash: Hash do sender_id
            session_id: ID determinístico da sessão
            tenant_id: ID do tenant
            vertente: Vertente de atendimento
            channel: Canal de origem

        Returns:
            Nova sessão (com ou sem histórico recuperado)
        """
        # Recuperar histórico do Firestore (se disponível)
        lead_profile = LeadProfile()
        recovered_history: list[HistoryEntry] = []

        if self._conversation_store is not None:
            try:
                lead_profile, recovered_history = await self._recover_from_firestore(
                    sender_hash, tenant_id
                )
                if lead_profile.name:
                    logger.info(
                        "session_history_recovered",
                        extra={
                            "sender_hash": sender_hash[:8],
                            "lead_name": bool(lead_profile.name),
                            "messages_recovered": len(recovered_history),
                        },
                    )
            except Exception as e:
                # Fallback: não bloqueia criação de sessão por erro no Firestore
                logger.warning(
                    "session_recovery_failed",
                    extra={"error": str(e), "sender_hash": sender_hash[:8]},
                )

        return await self._create_new(
            sender_hash,
            session_id,
            tenant_id,
            vertente,
            lead_profile=lead_profile,
            recovered_history=recovered_history,
        )

    async def _recover_from_firestore(
        self,
        sender_hash: str,
        tenant_id: str,
    ) -> tuple[LeadProfile, list[HistoryEntry]]:
        """Recupera perfil e histórico do Firestore.

        Returns:
            Tuple com (LeadProfile, lista de HistoryEntry)
        """
        if self._conversation_store is None:
            return LeadProfile(), []

        # Busca lead e mensagens em paralelo
        lead_task = asyncio.create_task(
            self._conversation_store.get_lead(sender_hash, tenant_id=tenant_id)
        )
        messages_task = asyncio.create_task(
            self._conversation_store.get_messages(
                sender_hash,
                limit=DEFAULT_HISTORY_RECOVERY_LIMIT,
                tenant_id=tenant_id,
            )
        )

        lead_data, messages = await asyncio.gather(lead_task, messages_task)

        # Converte LeadData para LeadProfile
        lead_profile = LeadProfile()
        if lead_data is not None:
            lead_profile = LeadProfile(
                name=lead_data.name or None,
                email=lead_data.email or None,
                phone=sender_hash,
                primary_intent=lead_data.primary_intent or None,
            )

        # Converte ConversationMessage para HistoryEntry
        history: list[HistoryEntry] = []
        for msg in messages:
            role = HistoryRole.ASSISTANT if msg.role == "assistant" else HistoryRole.USER
            history.append(
                HistoryEntry(
                    role=role,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    detected_intent=msg.detected_intent or None,
                )
            )

        return lead_profile, history

    async def _create_new(
        self,
        sender_hash: str,
        session_id: str,
        tenant_id: str,
        vertente: str,
        *,
        lead_profile: LeadProfile | None = None,
        recovered_history: list[HistoryEntry] | None = None,
    ) -> Session:
        """Cria nova sessão com dados recuperados (se disponíveis).

        Args:
            sender_hash: Hash do sender_id
            session_id: ID determinístico da sessão
            tenant_id: ID do tenant
            vertente: Vertente de atendimento
            lead_profile: Perfil do lead (recuperado do Firestore)
            recovered_history: Histórico recuperado (limitado às últimas N msgs)
        """
        now = datetime.now(UTC)

        session = Session(
            session_id=session_id,
            sender_id=sender_hash,
            current_state=DEFAULT_INITIAL_STATE,
            context=SessionContext(tenant_id=tenant_id, vertente=vertente),
            history=recovered_history or [],
            lead_profile=lead_profile or LeadProfile(),
            turn_count=0,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(seconds=self._ttl_seconds),
        )

        await self._store.save_async(session.to_dict(), self._ttl_seconds)
        logger.info(
            "session_created",
            extra={
                "session_id": session_id,
                "recovered_lead": bool(lead_profile and lead_profile.name),
                "recovered_history_count": len(recovered_history or []),
            },
        )
        return session

    async def add_message(
        self,
        session: Session,
        content: str,
        role: HistoryRole,
        *,
        detected_intent: str | None = None,
        channel: str = "whatsapp",
        message_id: str | None = None,
    ) -> None:
        """Adiciona mensagem à sessão com dual-write.

        Write-through pattern:
            1. Adiciona ao histórico da sessão (Redis sync)
            2. Persiste no Firestore (async, não bloqueia)

        Args:
            session: Sessão ativa
            content: Conteúdo da mensagem (sanitizado)
            role: Role da mensagem (user/assistant)
            detected_intent: Intenção detectada
            channel: Canal de origem
            message_id: ID único da mensagem (gerado se não fornecido)
        """
        # 1. Adiciona ao histórico local (Redis)
        session.add_to_history(content, role, detected_intent)
        await self.save(session)

        # 2. Dual-write para Firestore (async, fire-and-forget)
        if self._conversation_store is not None:
            # Fire-and-forget: não bloqueamos o fluxo principal
            asyncio.create_task(  # noqa: RUF006
                self._persist_message_to_firestore(
                    session=session,
                    content=content,
                    role=role,
                    detected_intent=detected_intent,
                    channel=channel,
                    message_id=message_id,
                )
            )

    async def _persist_message_to_firestore(
        self,
        session: Session,
        content: str,
        role: HistoryRole,
        *,
        detected_intent: str | None,
        channel: str,
        message_id: str | None,
    ) -> None:
        """Persiste mensagem no Firestore (background task).

        Não bloqueia o fluxo principal e não propaga exceções.
        """
        from app.protocols.conversation_store import ConversationMessage

        try:
            msg_id = message_id or f"{datetime.now(UTC).timestamp()}_{uuid.uuid4().hex[:8]}"
            message = ConversationMessage(
                message_id=msg_id,
                role="assistant" if role == HistoryRole.ASSISTANT else "user",
                content=content,
                timestamp=datetime.now(UTC),
                channel=channel,
                detected_intent=detected_intent or "",
            )

            await self._conversation_store.append_message(
                phone_hash=session.sender_id,
                message=message,
                tenant_id=session.context.tenant_id or "default",
            )

            logger.debug(
                "message_persisted_firestore",
                extra={
                    "session_id": session.session_id,
                    "message_id": msg_id,
                    "role": role.value,
                },
            )
        except Exception as e:
            # Log error but don't block the flow
            logger.warning(
                "firestore_persist_failed",
                extra={"error": str(e), "session_id": session.session_id},
            )

    async def update_lead_profile(
        self,
        session: Session,
        *,
        name: str | None = None,
        email: str | None = None,
        primary_intent: str | None = None,
    ) -> None:
        """Atualiza perfil do lead na sessão e persiste no Firestore.

        Args:
            session: Sessão ativa
            name: Nome do lead
            email: Email do lead
            primary_intent: Intenção principal
        """
        # Atualiza perfil local
        if name:
            session.lead_profile.name = name
        if email:
            session.lead_profile.email = email
        if primary_intent:
            session.lead_profile.primary_intent = primary_intent

        await self.save(session)

        # Dual-write para Firestore (fire-and-forget)
        if self._conversation_store is not None:
            asyncio.create_task(self._persist_lead_to_firestore(session))  # noqa: RUF006

    async def _persist_lead_to_firestore(self, session: Session) -> None:
        """Persiste lead no Firestore (background task)."""
        from app.protocols.conversation_store import LeadData

        try:
            lead = LeadData(
                phone_hash=session.sender_id,
                name=session.lead_profile.name or "",
                email=session.lead_profile.email or "",
                primary_intent=session.lead_profile.primary_intent or "",
                tenant_id=session.context.tenant_id or "default",
                last_contact=datetime.now(UTC),
            )
            await self._conversation_store.upsert_lead(lead)
            logger.debug(
                "lead_persisted_firestore",
                extra={"session_id": session.session_id},
            )
        except Exception as e:
            logger.warning(
                "firestore_lead_persist_failed",
                extra={"error": str(e), "session_id": session.session_id},
            )

    async def save(self, session: Session) -> None:
        """Persiste sessão atualizada."""
        await self._store.save_async(session.to_dict(), self._ttl_seconds)
        logger.debug("session_saved", extra={"session_id": session.session_id})

    async def close(self, session: Session, reason: str = "normal") -> None:
        """Encerra sessão explicitamente."""
        await self._store.delete_async(session.session_id)
        logger.info("session_closed", extra={"session_id": session.session_id, "reason": reason})
