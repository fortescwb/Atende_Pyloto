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
# Nota: palavras como "cpf" em contexto de instrução ("não exponha CPF") são aceitáveis
PII_PATTERNS_REAL_DATA = [
    "email@",
    "telefone:",
    "celular:",
    "cartao:",
    "credito:",
    "11999999999",  # número de telefone
    "123.456.789-00",  # CPF formatado
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

    def test_system_prompt_requires_3_candidates(self) -> None:
        """System prompt exige 3 candidatos."""
        assert "EXATAMENTE 3" in RESPONSE_AGENT_SYSTEM

    def test_system_prompt_lists_tones(self) -> None:
        """System prompt lista tons."""
        assert "formal" in RESPONSE_AGENT_SYSTEM
        assert "casual" in RESPONSE_AGENT_SYSTEM
        assert "empathetic" in RESPONSE_AGENT_SYSTEM

    def test_format_with_valid_input(self) -> None:
        """Formata prompt com inputs válidos."""
        result = format_response_agent_prompt(
            user_input="Preciso de ajuda",
            detected_intent="HELP_REQUEST",
            current_state="TRIAGE",
            next_state="COLLECTING_INFO",
            session_context="Cliente novo",
        )
        assert "Preciso de ajuda" in result
        assert "HELP_REQUEST" in result
        assert "Cliente novo" in result

    def test_format_with_empty_context(self) -> None:
        """Formata prompt com contexto vazio."""
        result = format_response_agent_prompt(
            user_input="Olá",
            detected_intent="GREETING",
            current_state="INITIAL",
            next_state="TRIAGE",
            session_context="",
        )
        assert "Nenhum contexto adicional" in result

    def test_template_no_pii(self) -> None:
        """Template não contém dados PII reais."""
        content = RESPONSE_AGENT_SYSTEM + RESPONSE_AGENT_USER_TEMPLATE
        for pattern in PII_PATTERNS_REAL_DATA:
            assert pattern.lower() not in content.lower()


class TestMessageTypeAgentPrompt:
    """Testes do prompt MessageTypeAgent."""

    def test_system_prompt_lists_types(self) -> None:
        """System prompt lista tipos de mensagem."""
        assert "text" in MESSAGE_TYPE_AGENT_SYSTEM
        assert "interactive_button" in MESSAGE_TYPE_AGENT_SYSTEM
        assert "interactive_list" in MESSAGE_TYPE_AGENT_SYSTEM
        assert "reaction" in MESSAGE_TYPE_AGENT_SYSTEM

    def test_format_with_options(self) -> None:
        """Formata prompt com opções."""
        result = format_message_type_agent_prompt(
            text_content="Escolha uma opção",
            options=["Sim", "Não"],
            intent_type="CONFIRMATION",
            user_input="Posso confirmar?",
        )
        assert "Escolha uma opção" in result
        assert "Sim, Não" in result
        assert "CONFIRMATION" in result

    def test_format_without_options(self) -> None:
        """Formata prompt sem opções."""
        result = format_message_type_agent_prompt(
            text_content="Texto simples",
            options=None,
            intent_type="",
            user_input="Olá",
        )
        assert "Nenhuma opção" in result
        assert "Não especificado" in result

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
        assert "3 falhas" in DECISION_AGENT_SYSTEM

    def test_system_prompt_mentions_fallback(self) -> None:
        """System prompt contém fallback."""
        assert "Desculpe, não entendi" in DECISION_AGENT_SYSTEM

    def test_format_with_all_inputs(self) -> None:
        """Formata prompt com todos inputs."""
        result = format_decision_agent_prompt(
            state_agent_output='{"current_state": "TRIAGE"}',
            response_agent_output='{"candidates": []}',
            message_type_agent_output='{"message_type": "text"}',
            user_input="Teste",
            consecutive_low_confidence=2,
        )
        assert "STATE AGENT" in result
        assert "RESPONSE AGENT" in result
        assert "MESSAGE TYPE AGENT" in result
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
