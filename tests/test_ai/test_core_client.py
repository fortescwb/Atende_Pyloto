"""Testes para ai/core/client.py.

Valida Protocol e MockAIClient.
"""

from typing import TYPE_CHECKING

import pytest

from ai.core.mock_client import MockAIClient
from ai.models.event_detection import EventDetectionRequest, EventDetectionResult
from ai.models.message_type_selection import (
    MessageTypeSelectionRequest,
    MessageTypeSelectionResult,
)
from ai.models.response_generation import (
    ResponseGenerationRequest,
    ResponseGenerationResult,
)

if TYPE_CHECKING:
    from ai.core.client import AIClientProtocol


class TestMockAIClient:
    """Testes para MockAIClient."""

    @pytest.fixture
    def client(self) -> MockAIClient:
        """Cria cliente mock para testes."""
        return MockAIClient()

    @pytest.mark.asyncio
    async def test_detect_event_greeting(self, client: MockAIClient) -> None:
        """Valida detecção de saudação."""
        request = EventDetectionRequest(user_input="Olá, bom dia!")

        result = await client.detect_event(request)

        assert isinstance(result, EventDetectionResult)
        assert result.detected_intent == "GREETING"
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_detect_event_support(self, client: MockAIClient) -> None:
        """Valida detecção de suporte."""
        request = EventDetectionRequest(user_input="Preciso de ajuda com um problema")

        result = await client.detect_event(request)

        assert isinstance(result, EventDetectionResult)
        assert result.detected_intent == "SUPPORT_REQUEST"

    @pytest.mark.asyncio
    async def test_detect_event_pricing(self, client: MockAIClient) -> None:
        """Valida detecção de pergunta sobre preço."""
        request = EventDetectionRequest(user_input="Qual o valor do serviço?")

        result = await client.detect_event(request)

        assert isinstance(result, EventDetectionResult)
        assert result.detected_intent == "PRICING_INQUIRY"

    @pytest.mark.asyncio
    async def test_detect_event_unknown(self, client: MockAIClient) -> None:
        """Valida detecção de intent desconhecido."""
        request = EventDetectionRequest(user_input="xpto abc 123")

        result = await client.detect_event(request)

        assert isinstance(result, EventDetectionResult)
        assert result.detected_intent == "ENTRY_UNKNOWN"

    @pytest.mark.asyncio
    async def test_generate_response(self, client: MockAIClient) -> None:
        """Valida geração de resposta."""
        request = ResponseGenerationRequest(
            event="USER_SENT_TEXT",
            detected_intent="GREETING",
            current_state="ENTRY",
            next_state="MENU",
            user_input="Olá",
        )

        result = await client.generate_response(request)

        assert isinstance(result, ResponseGenerationResult)
        assert result.text_content != ""
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_generate_response_support(self, client: MockAIClient) -> None:
        """Valida resposta para suporte."""
        request = ResponseGenerationRequest(
            event="USER_SENT_TEXT",
            detected_intent="SUPPORT_REQUEST",
            current_state="ENTRY",
            next_state="SUPPORT",
            user_input="Ajuda",
        )

        result = await client.generate_response(request)

        assert isinstance(result, ResponseGenerationResult)
        assert "ajuda" in result.text_content.lower()

    @pytest.mark.asyncio
    async def test_select_message_type_simple(self, client: MockAIClient) -> None:
        """Valida seleção de texto simples."""
        request = MessageTypeSelectionRequest(
            text_content="Olá, como vai?",
            options=[],
        )

        result = await client.select_message_type(request)

        assert isinstance(result, MessageTypeSelectionResult)
        assert result.message_type == "text"

    @pytest.mark.asyncio
    async def test_select_message_type_with_options(
        self, client: MockAIClient
    ) -> None:
        """Valida seleção com opções (usa botões)."""
        request = MessageTypeSelectionRequest(
            text_content="Escolha:",
            options=[
                {"id": "1", "title": "Suporte"},
                {"id": "2", "title": "Vendas"},
            ],
        )

        result = await client.select_message_type(request)

        assert isinstance(result, MessageTypeSelectionResult)
        assert result.message_type == "interactive_button"


class TestAIClientProtocol:
    """Testes para AIClientProtocol."""

    def test_mock_client_is_protocol_compliant(self) -> None:
        """Valida que MockAIClient implementa o Protocol."""
        # Se MockAIClient implementa todos os métodos do Protocol,
        # deve ser aceito em contextos que esperam AIClientProtocol
        client: AIClientProtocol = MockAIClient()
        assert hasattr(client, "detect_event")
        assert hasattr(client, "generate_response")
        assert hasattr(client, "select_message_type")
