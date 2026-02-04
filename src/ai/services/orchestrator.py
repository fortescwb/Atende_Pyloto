"""Orquestrador de IA — coordena 4 pontos de LLM com fallbacks.

Conforme README.md: 4 agentes LLM em sequência.
Agentes 1-3 em paralelo, Agente 4 consolida.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ai.models.decision_agent import (
    DecisionAgentRequest,
    DecisionAgentResult,
)
from ai.models.message_type_selection import (
    MessageTypeSelectionRequest,
    MessageTypeSelectionResult,
)
from ai.models.response_generation import (
    ResponseGenerationRequest,
    ResponseGenerationResult,
)
from ai.models.state_agent import StateAgentRequest, StateAgentResult
from ai.services._orchestrator_helpers import (
    calculate_4agent_confidence,
)
from ai.utils.sanitizer import sanitize_pii

if TYPE_CHECKING:
    from ai.config.settings import AISettings
    from ai.core.client import AIClientProtocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OrchestratorResult:
    """Resultado consolidado do orquestrador com resultados dos 4 agentes LLM."""

    state_suggestion: StateAgentResult
    response_generation: ResponseGenerationResult
    message_type_selection: MessageTypeSelectionResult
    final_decision: DecisionAgentResult
    overall_confidence: float
    understood: bool
    should_escalate: bool


class AIOrchestrator:
    """Orquestrador de IA — coordena 4 agentes em pipeline."""

    def __init__(
        self,
        client: AIClientProtocol,
        settings: AISettings | None = None,
    ) -> None:
        """Inicializa orquestrador com client e settings."""
        from ai.config.settings import get_ai_settings

        self._client = client
        self._settings = settings or get_ai_settings()
        self._consecutive_low_confidence = 0

    async def process_message(
        self,
        user_input: str,
        current_state: str = "INITIAL",
        session_history: list[str] | None = None,
        valid_transitions: tuple[str, ...] | None = None,
        session_context: dict[str, str] | None = None,
    ) -> OrchestratorResult:
        """Processa mensagem através dos 4 agentes LLM."""
        sanitized_input = sanitize_pii(user_input)
        transitions = valid_transitions or ("TRIAGE",)

        logger.debug("Processing via 4-agent pipeline", extra={"state": current_state})

        # Fase 1: Agentes 1, 2, 3 em paralelo
        state_result, response_result, message_type_result = await asyncio.gather(
            self._suggest_state(sanitized_input, current_state, session_history, transitions),
            self._generate_response(sanitized_input, current_state, session_context),
            self._select_message_type_simple(sanitized_input),
        )

        # Fase 2: Agente 4 (decisor) consolida outputs
        decision_result = await self._make_decision(
            state_result, response_result, message_type_result, sanitized_input,
        )

        # Atualiza contador de baixa confiança
        if decision_result.understood:
            self._consecutive_low_confidence = 0
        else:
            self._consecutive_low_confidence += 1

        overall = calculate_4agent_confidence(state_result, response_result, message_type_result)

        return OrchestratorResult(
            state_suggestion=state_result,
            response_generation=response_result,
            message_type_selection=message_type_result,
            final_decision=decision_result,
            overall_confidence=overall,
            understood=decision_result.understood,
            should_escalate=decision_result.should_escalate,
        )

    async def _suggest_state(
        self,
        user_input: str,
        current_state: str,
        session_history: list[str] | None,
        valid_transitions: tuple[str, ...],
    ) -> StateAgentResult:
        """Executa agente 1: sugestão de estado."""
        history = "\n".join(session_history or [])
        request = StateAgentRequest(
            user_input=user_input,
            current_state=current_state,
            conversation_history=history,
            valid_transitions=valid_transitions,
        )
        return await self._client.suggest_state(request)

    async def _generate_response(
        self,
        user_input: str,
        current_state: str,
        session_context: dict[str, str] | None,
    ) -> ResponseGenerationResult:
        """Executa agente 2: geração de resposta."""
        request = ResponseGenerationRequest(
            event="message",
            detected_intent="general",
            current_state=current_state,
            next_state=current_state,
            user_input=user_input,
            confidence_event=0.8,
            session_context=session_context or {},
        )
        return await self._client.generate_response(request)

    async def _select_message_type_simple(self, user_input: str) -> MessageTypeSelectionResult:
        """Executa agente 3: seleção de tipo de mensagem."""
        request = MessageTypeSelectionRequest(text_content=user_input, options=[])
        return await self._client.select_message_type(request)

    async def _make_decision(
        self,
        state_result: StateAgentResult,
        response_result: ResponseGenerationResult,
        message_type_result: MessageTypeSelectionResult,
        user_input: str,
    ) -> DecisionAgentResult:
        """Executa agente 4: decisão final."""
        request = DecisionAgentRequest(
            state_result=state_result,
            response_result=response_result,
            message_type_result=message_type_result,
            user_input=user_input,
            consecutive_low_confidence=self._consecutive_low_confidence,
        )
        return await self._client.make_decision(request)
