"""Teste de integração E2E — verifica fluxo completo de contexto e persistência.

Simula:
    1. Criação de sessão com recovery
    2. Adição de mensagens com dual-write
    3. Extração de dados do lead
    4. Geração de prompts com contexto institucional
    5. Atualização de perfil do lead
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from ai.config import get_institutional_prompt_section, load_institutional_context
from ai.prompts import (
    DECISION_AGENT_SYSTEM,
    MESSAGE_TYPE_AGENT_SYSTEM,
    RESPONSE_AGENT_SYSTEM,
    STATE_AGENT_SYSTEM,
    format_decision_agent_prompt,
    format_message_type_agent_prompt,
    format_response_agent_prompt,
    format_state_agent_prompt,
)
from ai.services import extract_lead_data, merge_lead_data
from app.protocols.conversation_store import ConversationMessage, LeadData
from app.sessions.manager import SessionManager
from app.sessions.models import HistoryRole

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_session_store() -> AsyncMock:
    """Store de sessão mock (Redis)."""
    store = AsyncMock()
    store.load_async = AsyncMock(return_value=None)
    store.save_async = AsyncMock()
    store.delete_async = AsyncMock()
    return store


@pytest.fixture
def mock_conversation_store() -> AsyncMock:
    """Store de conversas mock (Firestore)."""
    store = AsyncMock()
    # Simula lead existente que voltou
    store.get_lead = AsyncMock(
        return_value=LeadData(
            phone_hash="abc123",
            name="Maria Silva",
            email="maria@exemplo.com",
            primary_intent="sob_medida",
            tenant_id="tenant-001",
            first_contact=datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC),
            last_contact=datetime(2026, 1, 20, 14, 30, 0, tzinfo=UTC),
        )
    )
    # Simula histórico anterior
    store.get_messages = AsyncMock(
        return_value=[
            ConversationMessage(
                message_id="msg_001",
                role="user",
                content="Olá, preciso de um sistema para minha advocacia",
                timestamp=datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC),
                channel="whatsapp",
                detected_intent="SOB_MEDIDA",
            ),
            ConversationMessage(
                message_id="msg_002",
                role="assistant",
                content="Olá Maria! Entendo, sistemas sob medida para advocacia. Posso ajudar!",
                timestamp=datetime(2026, 1, 15, 10, 1, 0, tzinfo=UTC),
                channel="whatsapp",
            ),
        ]
    )
    store.append_message = AsyncMock()
    store.upsert_lead = AsyncMock()
    return store


# ──────────────────────────────────────────────────────────────────────────────
# Testes E2E
# ──────────────────────────────────────────────────────────────────────────────


class TestE2EFlowCompleto:
    """Testes de fluxo completo E2E."""

    @pytest.mark.asyncio
    async def test_fluxo_sessao_com_recovery(
        self,
        mock_session_store: AsyncMock,
        mock_conversation_store: AsyncMock,
    ) -> None:
        """Usuário volta após dias — recupera contexto do Firestore."""
        manager = SessionManager(
            store=mock_session_store,
            conversation_store=mock_conversation_store,
        )

        # Usuário volta — não tem sessão no Redis
        session = await manager.resolve_or_create(
            sender_id="5511999998888",
            tenant_id="tenant-001",
            vertente="vendas",
        )

        # Deve ter recuperado perfil do lead
        assert session.lead_profile.name == "Maria Silva"
        assert session.lead_profile.email == "maria@exemplo.com"
        assert session.lead_profile.primary_intent == "sob_medida"

        # Deve ter recuperado histórico
        assert len(session.history) == 2
        assert session.history[0].role == HistoryRole.USER
        assert "advocacia" in session.history[0].content

    @pytest.mark.asyncio
    async def test_adicionar_mensagem_com_dual_write(
        self,
        mock_session_store: AsyncMock,
        mock_conversation_store: AsyncMock,
    ) -> None:
        """Adiciona mensagem — salva no Redis e dispara task para Firestore."""
        manager = SessionManager(
            store=mock_session_store,
            conversation_store=mock_conversation_store,
        )

        session = await manager.resolve_or_create(
            sender_id="5511999998888",
            tenant_id="tenant-001",
        )
        mock_session_store.save_async.reset_mock()
        mock_conversation_store.append_message.reset_mock()

        # Adiciona mensagem do usuário
        await manager.add_message(
            session=session,
            content="Quanto custa um sistema para advocacia?",
            role=HistoryRole.USER,
            detected_intent="PRICING_INQUIRY",
        )

        # Aguarda tasks pendentes
        await asyncio.sleep(0.1)

        # Redis deve ter sido chamado
        assert mock_session_store.save_async.called

        # Firestore deve ter sido chamado
        assert mock_conversation_store.append_message.called
        call_args = mock_conversation_store.append_message.call_args
        assert call_args.kwargs["tenant_id"] == "tenant-001"

    def test_contexto_institucional_carrega(self) -> None:
        """Contexto institucional carrega corretamente."""
        ctx = load_institutional_context()

        # Estrutura esperada
        assert "empresa" in ctx
        assert "contato" in ctx
        assert "vertentes" in ctx
        assert "horario_atendimento_presencial" in ctx

        # Dados da empresa
        assert ctx["empresa"]["nome"] == "Pyloto"

    def test_prompt_inclui_contexto_institucional(self) -> None:
        """Prompts incluem informações institucionais."""
        prompt_section = get_institutional_prompt_section()

        # Deve conter informações da empresa
        assert "Pyloto" in prompt_section
        assert any(
            word in prompt_section.lower()
            for word in ["contato", "telefone", "email", "endereço"]
        )

    def test_state_agent_prompt_formata_corretamente(self) -> None:
        """StateAgent prompt formata corretamente com parâmetros."""
        prompt_user = format_state_agent_prompt(
            user_input="Olá, quero saber sobre sistemas",
            current_state="INITIAL",
            conversation_history="Usuário: Oi\nOtto: Olá, como posso ajudar?",
            valid_transitions=("TRIAGE", "GREETING"),
        )

        # StateAgent é minimalista - foca em seleção de estado, não em contexto institucional
        # O contexto institucional está no ResponseAgent
        assert "state" in STATE_AGENT_SYSTEM.lower()
        # Deve conter a mensagem do usuário no template formatado
        assert "quero saber sobre sistemas" in prompt_user
        # Deve conter transições válidas
        assert "TRIAGE" in prompt_user

    def test_response_agent_prompt_formata_corretamente(self) -> None:
        """ResponseAgent prompt formata corretamente."""
        prompt_user = format_response_agent_prompt(
            user_input="Quanto custa?",
            current_state="TRIAGE",
            lead_profile="Nome: Carlos\nVertente: vendas",
            is_first_message=False,
        )

        # Deve conter o lead profile
        assert "Carlos" in prompt_user
        # Deve conter contexto institucional no system
        assert "Pyloto" in RESPONSE_AGENT_SYSTEM

    def test_extracao_lead_funciona(self) -> None:
        """Extração de lead funciona com padrões esperados."""
        # Teste com email e nome
        data1 = extract_lead_data("Meu nome é Carlos, email carlos@empresa.com")
        assert data1.name == "Carlos"
        assert data1.email == "carlos@empresa.com"

        # Teste com telefone
        data2 = extract_lead_data("Me liga em 11 99999-8888")
        assert data2.phone == "11999998888"

        # Teste merge
        merged = merge_lead_data(data1, data2)
        assert merged.name == "Carlos"
        assert merged.email == "carlos@empresa.com"
        assert merged.phone == "11999998888"

    @pytest.mark.asyncio
    async def test_atualizar_lead_profile(
        self,
        mock_session_store: AsyncMock,
        mock_conversation_store: AsyncMock,
    ) -> None:
        """Atualizar perfil do lead persiste no Firestore."""
        manager = SessionManager(
            store=mock_session_store,
            conversation_store=mock_conversation_store,
        )

        session = await manager.resolve_or_create(
            sender_id="5511999998888",
            tenant_id="tenant-001",
        )
        mock_conversation_store.upsert_lead.reset_mock()

        # Atualiza perfil
        await manager.update_lead_profile(
            session,
            name="Maria Atualizado",
            primary_intent="parceria",
        )

        # Aguarda tasks
        await asyncio.sleep(0.1)

        # Perfil local deve estar atualizado
        assert session.lead_profile.name == "Maria Atualizado"
        assert session.lead_profile.primary_intent == "parceria"
        # Email deve manter (não foi passado para atualização)
        assert session.lead_profile.email == "maria@exemplo.com"

        # Firestore deve ter sido chamado
        assert mock_conversation_store.upsert_lead.called

    def test_history_as_strings_backwards_compat(self) -> None:
        """history_as_strings mantém compatibilidade."""
        from app.sessions.models import Session

        session = Session(
            session_id="test-123",
            sender_id="sender-hash",
        )
        session.add_to_history("Mensagem 1", HistoryRole.USER)
        session.add_to_history("Resposta 1", HistoryRole.ASSISTANT)

        strings = session.history_as_strings
        assert len(strings) == 2
        assert "Usuário: Mensagem 1" in strings[0]
        assert "Otto: Resposta 1" in strings[1]


class TestIntegracaoPrompts:
    """Testes de integração dos prompts com contexto."""

    def test_todos_prompts_compilam(self) -> None:
        """Todos os prompts formatadores compilam sem erro."""
        # StateAgent
        state_user = format_state_agent_prompt(
            user_input="Teste",
            current_state="INITIAL",
            conversation_history="",
            valid_transitions=("TRIAGE",),
        )
        assert isinstance(state_user, str)
        assert "Teste" in state_user

        # ResponseAgent
        response_user = format_response_agent_prompt(
            user_input="Teste",
            detected_intent="GENERAL",
            current_state="TRIAGE",
            next_state="TRIAGE",
        )
        assert isinstance(response_user, str)
        assert "Teste" in response_user

        # MessageTypeAgent
        msgtype_user = format_message_type_agent_prompt(
            text_content="Olá, como posso ajudar?",
        )
        assert isinstance(msgtype_user, str)
        assert "Olá" in msgtype_user

        # DecisionAgent
        decision_user = format_decision_agent_prompt(
            state_agent_output='{"detected_intent": "GENERAL"}',
            response_agent_output='[{"text": "Olá!"}]',
            message_type_agent_output='{"type": "text"}',
            user_input="Teste",
        )
        assert isinstance(decision_user, str)
        assert "Teste" in decision_user

    def test_system_prompts_contem_contexto(self) -> None:
        """System prompts contêm contexto institucional."""
        # ResponseAgent tem contexto institucional completo (é o agente conversacional)
        assert "Pyloto" in RESPONSE_AGENT_SYSTEM
        # StateAgent é minimalista - foco em seleção de estado
        assert "state" in STATE_AGENT_SYSTEM.lower()
        # MessageType e Decision são mais técnicos, podem não ter
        assert MESSAGE_TYPE_AGENT_SYSTEM  # Não vazio
        assert DECISION_AGENT_SYSTEM  # Não vazio
