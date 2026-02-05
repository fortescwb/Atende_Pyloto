"""Orquestrador de IA — coordena 5 pontos de LLM com fallbacks.

Arquitetura de execução (validada):
- Fase 1: StateAgent (nano), ResponseAgent (Chat), ContactCardExtractor (nano) em paralelo
- Fase 2: MessageTypeAgent (nano) — recebe estado + resposta
- Fase 3: DecisionAgent (GPT-5.1) — consolida tudo

Regras:
- StateAgent: reasoning baixo, consistência máxima
- ResponseAgent: só verbaliza, NUNCA decide estado, recebe ContactCard
- ContactCardExtractor: extrai dados para persistência (nome, necessidades, etc)
- MessageTypeAgent: classificação pura, prompt ultra-restritivo
- DecisionAgent: mesmo modelo do StateAgent para calibração de confiança
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ai.models.contact_card_extraction import (
    ContactCardExtractionRequest,
    ContactCardExtractionResult,
)
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
from ai.utils.sanitizer import mask_history, sanitize_pii

if TYPE_CHECKING:
    from ai.config.settings import AISettings
    from ai.core.client import AIClientProtocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OrchestratorResult:
    """Resultado consolidado do orquestrador com resultados dos 5 agentes LLM."""

    state_suggestion: StateAgentResult
    response_generation: ResponseGenerationResult
    contact_card_extraction: ContactCardExtractionResult
    message_type_selection: MessageTypeSelectionResult
    final_decision: DecisionAgentResult
    overall_confidence: float
    understood: bool
    should_escalate: bool


class AIOrchestrator:
    """Orquestrador de IA — coordena 5 agentes em pipeline."""

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
        contact_card_summary: str = "",
        is_first_message: bool = False,
        skip_contact_card_extraction: bool = False,
    ) -> OrchestratorResult:
        """Processa mensagem através dos 5 agentes LLM.

        Fluxo:
        1. StateAgent + ResponseAgent + ContactCardExtractor em paralelo
        2. MessageTypeAgent (recebe estado decidido + resposta gerada)
        3. DecisionAgent (consolida tudo e pode contradizer)
        """
        sanitized_input = sanitize_pii(user_input)
        transitions = valid_transitions or ("TRIAGE",)

        logger.debug("Processing via 5-agent pipeline", extra={"state": current_state})

        # Fase 1: StateAgent, ResponseAgent e ContactCardExtractor em paralelo
        # Todos os 3 usam modelos rápidos (nano/chat) para baixa latência
        tasks = [
            self._suggest_state(sanitized_input, current_state, session_history, transitions),
            self._generate_response(
                sanitized_input,
                current_state,
                session_context,
                detected_intent="general",  # Será refinado pelo DecisionAgent
                session_history=session_history,
                valid_transitions=transitions,
                contact_card_summary=contact_card_summary,
                is_first_message=is_first_message,
            ),
        ]
        if not skip_contact_card_extraction:
            tasks.append(self._extract_contact_card(sanitized_input, contact_card_summary))

        results = await asyncio.gather(*tasks)
        state_result, response_result = results[0], results[1]
        if skip_contact_card_extraction:
            contact_card_result = ContactCardExtractionResult.empty()
        else:
            contact_card_result = results[2]

        # Fase 2: MessageTypeAgent (nano) — classificação pura
        # Recebe: estado decidido + resposta gerada
        message_type_result = await self._select_message_type(
            text_content=response_result.text_content,
            suggested_state=state_result.current_state,
            detected_intent=state_result.detected_intent,
            user_input=sanitized_input,
        )

        # Fase 3: DecisionAgent (GPT-5.1) — consolida e pode contradizer
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
            contact_card_extraction=contact_card_result,
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
        detected_intent: str = "general",
        session_history: list[str] | None = None,
        valid_transitions: tuple[str, ...] | None = None,
        contact_card_summary: str = "",
        is_first_message: bool = False,
    ) -> ResponseGenerationResult:
        """Executa agente 2: geração de resposta (gpt-5-chat-latest).

        REGRA: Chat SÓ verbaliza, NUNCA decide estado.
        Recebe ContactCard para personalizacao.

        Args:
            user_input: Mensagem do usuário
            current_state: Estado atual da FSM
            session_context: Contexto da sessão
            detected_intent: Intenção (refinada pelo DecisionAgent)
            session_history: Histórico de mensagens (últimas N)
            valid_transitions: Estados possíveis (para contexto, não decisão)
            contact_card_summary: Contexto do ContactCard formatado
        """
        # Enriquece contexto com histórico, estados e lead profile
        enriched_context = dict(session_context or {})
        if session_history:
            enriched_context["conversation_history"] = "\n".join(session_history[-5:])
        if valid_transitions:
            enriched_context["possible_next_states"] = ", ".join(valid_transitions)
        if contact_card_summary:
            enriched_context["contact_card"] = contact_card_summary

        # Histórico sanitizado e truncado para prompt
        history_for_prompt = "\n".join(mask_history(session_history or [], max_messages=None))

        request = ResponseGenerationRequest(
            event="message",
            detected_intent=detected_intent,
            current_state=current_state,
            next_state=current_state,
            user_input=user_input,
            confidence_event=0.8,
            session_context=enriched_context,
        )
        # Passa histórico e lead profile direto ao prompt
        return await self._client.generate_response(
            request,
            conversation_history=history_for_prompt,
            contact_card=contact_card_summary,
            is_first_message=is_first_message,
        )

    async def _extract_contact_card(
        self,
        user_message: str,
        contact_card_summary: str,
    ) -> ContactCardExtractionResult:
        """Executa agente 2-B: extracao de dados do contato (gpt-5-nano).

        Extrai informacoes do usuario para salvar no ContactCard.
        Roda em paralelo com State e Response para não adicionar latência.

        Args:
            user_message: Mensagem do usuário
            contact_card_summary: Resumo do contato atual
        """
        request = ContactCardExtractionRequest(
            user_message=user_message,
            contact_card_summary=contact_card_summary,
        )
        return await self._client.extract_contact_card(request)

    async def _select_message_type(
        self,
        text_content: str,
        suggested_state: str,
        detected_intent: str | None,
        user_input: str,
    ) -> MessageTypeSelectionResult:
        """Executa agente 3: seleção de tipo de mensagem (GPT-5 nano).

        REGRA: Classificação pura. Prompt ultra-restritivo.
        Recebe estado decidido + resposta gerada.
        Retorna enum: TEXT | INTERACTIVE | REACTION | MEDIA.

        Args:
            text_content: Resposta gerada pelo ResponseAgent
            suggested_state: Estado sugerido pelo StateAgent
            detected_intent: Intenção detectada
            user_input: Mensagem original do usuário
        """
        # Passa contexto mínimo para classificação
        options = []  # Pode ser populado se houver botões/lista
        request = MessageTypeSelectionRequest(
            text_content=text_content,
            options=options,
        )
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
