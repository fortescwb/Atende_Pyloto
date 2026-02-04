"""Protocolo para clientes de IA.

Define o contrato AIClientProtocol para implementações concretas.
Conforme REGRAS_E_PADROES.md § 2.1: ai/core contém interfaces e pipeline.
Conforme REGRAS_E_PADROES.md § 3: ai/ não faz IO direto (HTTP via protocol).
Conforme README.md: 4 agentes LLM (State, Response, MessageType, Decision).
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ai.models.decision_agent import DecisionAgentRequest, DecisionAgentResult
    from ai.models.event_detection import EventDetectionRequest, EventDetectionResult
    from ai.models.message_type_selection import (
        MessageTypeSelectionRequest,
        MessageTypeSelectionResult,
    )
    from ai.models.response_generation import (
        ResponseGenerationRequest,
        ResponseGenerationResult,
    )
    from ai.models.state_agent import StateAgentRequest, StateAgentResult


class AIClientProtocol(Protocol):
    """Protocolo para clientes de IA.

    Define contrato para implementações concretas (OpenAI, mock, etc.).
    Permite injeção de dependência e testabilidade.
    """

    @abstractmethod
    async def detect_event(
        self,
        request: EventDetectionRequest,
    ) -> EventDetectionResult:
        """Detecta evento e intenção usando LLM.

        Args:
            request: Dados para detecção

        Returns:
            Resultado da detecção (ou fallback em caso de erro)
        """
        ...

    @abstractmethod
    async def generate_response(
        self,
        request: ResponseGenerationRequest,
    ) -> ResponseGenerationResult:
        """Gera resposta usando LLM.

        Args:
            request: Dados para geração

        Returns:
            Resposta gerada (ou fallback em caso de erro)
        """
        ...

    @abstractmethod
    async def select_message_type(
        self,
        request: MessageTypeSelectionRequest,
    ) -> MessageTypeSelectionResult:
        """Seleciona tipo de mensagem ideal usando LLM.

        Args:
            request: Dados para seleção

        Returns:
            Tipo selecionado (ou fallback em caso de erro)
        """
        ...

    @abstractmethod
    async def suggest_state(
        self,
        request: StateAgentRequest,
    ) -> StateAgentResult:
        """Sugere próximos estados válidos usando LLM #1 (StateAgent).

        Analisa o contexto da conversa e sugere transições de estado.

        Args:
            request: Dados para sugestão de estado

        Returns:
            Resultado com estados sugeridos (ou fallback em caso de erro)
        """
        ...

    @abstractmethod
    async def make_decision(
        self,
        request: DecisionAgentRequest,
    ) -> DecisionAgentResult:
        """Consolida outputs e toma decisão final usando LLM #4 (DecisionAgent).

        Analisa outputs dos 3 agentes anteriores e escolhe a melhor
        combinação de estado, resposta e tipo de mensagem.

        Args:
            request: Dados consolidados dos 3 agentes anteriores

        Returns:
            Decisão final consolidada (ou fallback em caso de erro)
        """
        ...
