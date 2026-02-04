"""Testes para prompts dos 4 agentes LLM.

Verifica formatação e ausência de PII.
"""

from __future__ import annotations

from ai.prompts.decision_agent_prompt import (
    DECISION_AGENT_SYSTEM,
    DECISION_AGENT_USER_TEMPLATE,
    format_decision_agent_prompt,
)
from ai.prompts.message_type_agent_prompt import (
    MESSAGE_TYPE_AGENT_SYSTEM,
    MESSAGE_TYPE_AGENT_USER_TEMPLATE,
    format_message_type_agent_prompt,
)
from ai.prompts.response_agent_prompt import (
    RESPONSE_AGENT_SYSTEM,
    RESPONSE_AGENT_USER_TEMPLATE,
    format_response_agent_prompt,
)
from ai.prompts.state_agent_prompt import (
    STATE_AGENT_SYSTEM,
    STATE_AGENT_USER_TEMPLATE,
    format_state_agent_prompt,
)

# Lista de padrões PII que não devem aparecer em prompts
# Nota: informações institucionais (contato da empresa) são permitidas
# PII proibida: dados de USUÁRIOS (clientes/leads)
PII_PATTERNS_REAL_DATA = [
    "usuario@email.com",  # email de usuário específico
    "cliente@",  # email de cliente
    "cartao:",  # dados de cartão
    "credito:",  # dados de crédito
    "cpf:",  # CPF
    "123.456.789-00",  # CPF formatado
    "rg:",  # RG
]


class TestStateAgentPrompt:
    """Testes do prompt StateAgent."""

    def test_system_prompt_contains_states(self) -> None:
        """System prompt lista estados FSM."""
        assert "INITIAL" in STATE_AGENT_SYSTEM
        assert "HANDOFF_HUMAN" in STATE_AGENT_SYSTEM
        assert "TRIAGE" in STATE_AGENT_SYSTEM

    def test_system_prompt_requires_json(self) -> None:
        """System prompt exige resposta JSON."""
        assert "JSON" in STATE_AGENT_SYSTEM

    def test_format_with_valid_input(self) -> None:
        """Formata prompt com inputs válidos."""
        result = format_state_agent_prompt(
            user_input="Olá",
            current_state="INITIAL",
            conversation_history="Nenhum",
            valid_transitions=("TRIAGE", "COLLECTING_INFO"),
        )
        assert "Olá" in result
        assert "INITIAL" in result
        assert "TRIAGE, COLLECTING_INFO" in result

    def test_format_with_empty_transitions(self) -> None:
        """Formata prompt com transições vazias."""
        result = format_state_agent_prompt(
            user_input="Olá",
            current_state="INITIAL",
            conversation_history="",
            valid_transitions=(),
        )
        assert "Nenhuma" in result

    def test_template_no_pii(self) -> None:
        """Template não contém dados PII reais."""
        content = STATE_AGENT_SYSTEM + STATE_AGENT_USER_TEMPLATE
        for pattern in PII_PATTERNS_REAL_DATA:
            assert pattern.lower() not in content.lower()


class TestResponseAgentPrompt:
    """Testes do prompt ResponseAgent."""

    def test_system_prompt_contains_json_format(self) -> None:
        """System prompt exige resposta JSON com text, tone, confidence."""
        assert "text" in RESPONSE_AGENT_SYSTEM
        assert "tone" in RESPONSE_AGENT_SYSTEM
        assert "confidence" in RESPONSE_AGENT_SYSTEM

    def test_system_prompt_mentions_otto(self) -> None:
        """System prompt define Otto como assistente."""
        assert "Otto" in RESPONSE_AGENT_SYSTEM
        assert "Pyloto" in RESPONSE_AGENT_SYSTEM

    def test_format_with_valid_input(self) -> None:
        """Formata prompt com inputs válidos."""
        result = format_response_agent_prompt(
            user_input="Preciso de ajuda",
            current_state="TRIAGE",
            lead_profile="Nome: João",
            is_first_message=False,
        )
        assert "Preciso de ajuda" in result
        assert "João" in result
        assert "TRIAGE" in result

    def test_format_with_empty_profile(self) -> None:
        """Formata prompt com perfil vazio."""
        result = format_response_agent_prompt(
            user_input="Olá",
            current_state="INITIAL",
            lead_profile="",
            is_first_message=True,
        )
        assert "Vazio" in result or "nenhuma informação" in result.lower()

    def test_template_no_pii(self) -> None:
        """Template não contém dados PII reais."""
        content = RESPONSE_AGENT_SYSTEM + RESPONSE_AGENT_USER_TEMPLATE
        for pattern in PII_PATTERNS_REAL_DATA:
            assert pattern.lower() not in content.lower()


class TestMessageTypeAgentPrompt:
    """Testes do prompt MessageTypeAgent (GPT-5 nano - minimalista)."""

    def test_system_prompt_lists_types(self) -> None:
        """System prompt lista tipos de mensagem."""
        assert "text" in MESSAGE_TYPE_AGENT_SYSTEM
        assert "interactive_button" in MESSAGE_TYPE_AGENT_SYSTEM
        assert "interactive_list" in MESSAGE_TYPE_AGENT_SYSTEM
        # Prompt minimalista para nano — apenas 3 tipos principais

    def test_format_with_options(self) -> None:
        """Formata prompt com opções (nano ignora options, simplificado)."""
        result = format_message_type_agent_prompt(
            text_content="Escolha uma opção",
            options=["Sim", "Não"],
            intent_type="CONFIRMATION",
            user_input="Posso confirmar?",
        )
        assert "Escolha uma opção" in result
        # Nano não recebe options no template (simplificado)
        assert "Classifique" in result

    def test_format_without_options(self) -> None:
        """Formata prompt sem opções (nano)."""
        result = format_message_type_agent_prompt(
            text_content="Texto simples",
            options=None,
            intent_type="",
            user_input="Olá",
        )
        # Nano usa template minimalista
        assert "Texto simples" in result
        assert "Classifique" in result

    def test_template_no_pii(self) -> None:
        """Template não contém dados PII reais."""
        content = MESSAGE_TYPE_AGENT_SYSTEM + MESSAGE_TYPE_AGENT_USER_TEMPLATE
        for pattern in PII_PATTERNS_REAL_DATA:
            assert pattern.lower() not in content.lower()


class TestDecisionAgentPrompt:
    """Testes do prompt DecisionAgent."""

    def test_system_prompt_mentions_threshold(self) -> None:
        """System prompt menciona threshold 0.7."""
        assert "0.7" in DECISION_AGENT_SYSTEM

    def test_system_prompt_mentions_escalation(self) -> None:
        """System prompt menciona escalação."""
        assert "should_escalate" in DECISION_AGENT_SYSTEM
        # O texto foi atualizado para "3+ falhas consecutivas"
        assert "3" in DECISION_AGENT_SYSTEM

    def test_system_prompt_mentions_understood(self) -> None:
        """System prompt contém campo understood."""
        assert "understood" in DECISION_AGENT_SYSTEM

    def test_format_with_all_inputs(self) -> None:
        """Formata prompt com todos inputs."""
        result = format_decision_agent_prompt(
            state_agent_output='{"next_state": "TRIAGE"}',
            response_agent_output='{"text": "Olá"}',
            message_type_agent_output='{"message_type": "text"}',
            user_input="Teste",
            consecutive_low_confidence=2,
        )
        # Novo template usa "Agente 1 (Estado)" etc.
        assert "Agente 1" in result
        assert "Agente 2" in result
        assert "Agente 3" in result
        assert "Falhas consecutivas: 2" in result

    def test_format_default_consecutive_failures(self) -> None:
        """Formata prompt com falhas padrão zero."""
        result = format_decision_agent_prompt(
            state_agent_output="{}",
            response_agent_output="{}",
            message_type_agent_output="{}",
            user_input="Olá",
        )
        assert "Falhas consecutivas: 0" in result

    def test_template_no_pii(self) -> None:
        """Template não contém dados PII reais."""
        content = DECISION_AGENT_SYSTEM + DECISION_AGENT_USER_TEMPLATE
        for pattern in PII_PATTERNS_REAL_DATA:
            assert pattern.lower() not in content.lower()
