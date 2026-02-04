"""Testes para ai/prompts/ — Pipeline de 4 Agentes.

Valida prompts e funções de formatação.
"""

from ai.prompts import (
    DECISION_AGENT_SYSTEM,
    MESSAGE_TYPE_AGENT_SYSTEM,
    RESPONSE_AGENT_SYSTEM,
    STATE_AGENT_SYSTEM,
    SYSTEM_ROLE,
    contains_sensitive_content,
    format_decision_agent_prompt,
    format_message_type_agent_prompt,
    format_response_agent_prompt,
    format_state_agent_prompt,
    get_expected_intents,
    get_sensitivity_level,
    get_state_context,
    is_intent_expected,
    requires_escalation,
)


class TestSystemPrompts:
    """Testes para system prompts."""

    def test_system_role_exists(self) -> None:
        """Valida que SYSTEM_ROLE está definido."""
        assert SYSTEM_ROLE is not None
        assert len(SYSTEM_ROLE) > 0
        assert "Pyloto" in SYSTEM_ROLE

    def test_state_agent_system(self) -> None:
        """Valida prompt do StateAgent (LLM #1)."""
        assert STATE_AGENT_SYSTEM is not None
        assert "JSON" in STATE_AGENT_SYSTEM
        assert "state" in STATE_AGENT_SYSTEM.lower()

    def test_response_agent_system(self) -> None:
        """Valida prompt do ResponseAgent (LLM #2)."""
        assert RESPONSE_AGENT_SYSTEM is not None
        assert "JSON" in RESPONSE_AGENT_SYSTEM
        assert "candidato" in RESPONSE_AGENT_SYSTEM.lower() or "resposta" in RESPONSE_AGENT_SYSTEM.lower()

    def test_message_type_agent_system(self) -> None:
        """Valida prompt do MessageTypeAgent (LLM #3)."""
        assert MESSAGE_TYPE_AGENT_SYSTEM is not None
        assert "JSON" in MESSAGE_TYPE_AGENT_SYSTEM
        assert "message_type" in MESSAGE_TYPE_AGENT_SYSTEM

    def test_decision_agent_system(self) -> None:
        """Valida prompt do DecisionAgent (LLM #4)."""
        assert DECISION_AGENT_SYSTEM is not None
        assert "JSON" in DECISION_AGENT_SYSTEM
        assert "final" in DECISION_AGENT_SYSTEM.lower()


class TestFormatPrompts:
    """Testes para funções de formatação dos 4 agentes."""

    def test_format_state_agent(self) -> None:
        """Valida formatação de prompt do StateAgent."""
        prompt = format_state_agent_prompt(
            user_input="Olá",
            current_state="INITIAL",
            conversation_history="",
            valid_transitions=("TRIAGE",),
        )

        assert "Olá" in prompt
        assert "INITIAL" in prompt
        assert "TRIAGE" in prompt

    def test_format_response_agent(self) -> None:
        """Valida formatação de prompt do ResponseAgent."""
        prompt = format_response_agent_prompt(
            user_input="Olá",
            detected_intent="GREETING",
            current_state="INITIAL",
            next_state="TRIAGE",
        )

        assert "Olá" in prompt
        assert "GREETING" in prompt

    def test_format_message_type_agent(self) -> None:
        """Valida formatação de prompt do MessageTypeAgent."""
        prompt = format_message_type_agent_prompt(
            text_content="Escolha uma opção:",
            options=["Suporte", "Vendas"],
        )

        assert "Escolha uma opção" in prompt
        assert "Suporte" in prompt

    def test_format_decision_agent(self) -> None:
        """Valida formatação de prompt do DecisionAgent."""
        prompt = format_decision_agent_prompt(
            state_agent_output='{"current_state": "INITIAL"}',
            response_agent_output='{"text_content": "Olá"}',
            message_type_agent_output='{"message_type": "text"}',
            user_input="Olá",
            consecutive_low_confidence=0,
        )

        assert "INITIAL" in prompt
        assert "Olá" in prompt


class TestStatePrompts:
    """Testes para prompts por estado."""

    def test_get_state_context_known(self) -> None:
        """Valida contexto de estado conhecido."""
        context = get_state_context("ENTRY")
        assert context is not None
        assert len(context) > 0

    def test_get_state_context_unknown(self) -> None:
        """Valida contexto de estado desconhecido."""
        context = get_state_context("ESTADO_INEXISTENTE")
        assert context is not None  # Retorna default

    def test_get_expected_intents(self) -> None:
        """Valida intents esperados para estado."""
        intents = get_expected_intents("ENTRY")
        assert isinstance(intents, tuple)
        assert len(intents) > 0
        assert "GREETING" in intents

    def test_is_intent_expected(self) -> None:
        """Valida verificação de intent esperado."""
        assert is_intent_expected("ENTRY", "GREETING") is True
        assert is_intent_expected("ENTRY", "INTENT_INEXISTENTE") is False


class TestValidationPrompts:
    """Testes para prompts de validação."""

    def test_contains_sensitive_content_true(self) -> None:
        """Valida detecção de conteúdo sensível."""
        assert contains_sensitive_content("Vou processar vocês") is True
        assert contains_sensitive_content("Quero meu reembolso") is True
        assert contains_sensitive_content("Vou chamar meu advogado") is True

    def test_contains_sensitive_content_false(self) -> None:
        """Valida ausência de conteúdo sensível."""
        assert contains_sensitive_content("Olá, bom dia") is False
        assert contains_sensitive_content("Qual o horário?") is False

    def test_requires_escalation_true(self) -> None:
        """Valida detecção de pedido de escalação."""
        assert requires_escalation("Preciso falar com humano agora") is True
        assert requires_escalation("Chame o supervisor por favor") is True
        assert requires_escalation("Quero atendimento humano") is True

    def test_requires_escalation_false(self) -> None:
        """Valida ausência de pedido de escalação."""
        assert requires_escalation("Olá, preciso de ajuda") is False

    def test_get_sensitivity_level(self) -> None:
        """Valida determinação de nível de sensibilidade."""
        assert get_sensitivity_level("Olá") == "low"
        assert get_sensitivity_level("Preciso de ajuda urgente") == "medium"
        assert get_sensitivity_level("Quero reembolso") == "high"
        assert get_sensitivity_level("Vou processar na justiça") == "critical"

    def test_get_sensitivity_level_escalation(self) -> None:
        """Valida que escalação retorna high."""
        level = get_sensitivity_level("Preciso falar com humano")
        assert level == "high"
