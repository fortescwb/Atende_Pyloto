"""Testes para o cliente OpenAI real — Pipeline de 4 Agentes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from ai.models.message_type_selection import MessageTypeSelectionRequest
from ai.models.response_generation import ResponseGenerationRequest
from ai.models.state_agent import StateAgentRequest
from app.infra.ai.openai_client import OpenAIClient


class TestOpenAIClientInit:
    """Testes de inicialização do cliente."""

    def test_init_with_defaults(self) -> None:
        """Verifica inicialização com valores padrão."""
        client = OpenAIClient()
        assert client._settings is not None
        assert client._http_client is None

    def test_init_with_api_key(self) -> None:
        """Verifica inicialização com API key."""
        client = OpenAIClient(api_key="test-key")
        assert client._api_key == "test-key"

    def test_init_with_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifica leitura de API key de env var."""
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        client = OpenAIClient()
        assert client._api_key == "env-key"


class TestOpenAIClientStateAgent:
    """Testes para sugestão de estado (StateAgent LLM #1)."""

    @pytest.mark.asyncio
    async def test_suggest_state_success(self) -> None:
        """Verifica sugestão de estado com sucesso."""
        client = OpenAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"previous_state": "INITIAL", "current_state": "INITIAL", "suggested_next_states": [{"state": "TRIAGE", "confidence": 0.9, "reasoning": "test"}], "confidence": 0.9, "rationale": "test"}'
                    }
                }
            ],
            "usage": {"total_tokens": 100}
        }
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_response
        client._http_client = mock_http

        request = StateAgentRequest(
            user_input="Olá, bom dia!",
            current_state="INITIAL",
            conversation_history="",
            valid_transitions=("TRIAGE",),
        )

        result = await client.suggest_state(request)

        assert result.current_state == "INITIAL"
        assert result.confidence == 0.9
        assert len(result.suggested_next_states) > 0

    @pytest.mark.asyncio
    async def test_suggest_state_fallback_on_no_api_key(self) -> None:
        """Verifica fallback quando não há API key."""
        client = OpenAIClient(api_key="")

        request = StateAgentRequest(
            user_input="Olá",
            current_state="INITIAL",
            conversation_history="",
            valid_transitions=("TRIAGE",),
        )

        result = await client.suggest_state(request)

        assert result.current_state == "INITIAL"
        assert "Fallback" in (result.rationale or "") or result.confidence < 1.0


class TestOpenAIClientResponseGeneration:
    """Testes para geração de resposta (ResponseAgent LLM #2)."""

    @pytest.mark.asyncio
    async def test_generate_response_success(self) -> None:
        """Verifica geração de resposta com sucesso."""
        client = OpenAIClient(api_key="test-key")

        # ResponseAgent retorna candidatos
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"candidates": [{"text_content": "Olá! Como posso ajudar?", "tone": "FORMAL", "confidence": 0.85, "rationale": "greeting response"}]}'
                    }
                }
            ],
            "usage": {"total_tokens": 150}
        }
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_response
        client._http_client = mock_http

        request = ResponseGenerationRequest(
            event="USER_SENT_TEXT",
            detected_intent="GREETING",
            current_state="INITIAL",
            next_state="TRIAGE",
            user_input="Olá",
        )

        result = await client.generate_response(request)

        assert "Olá" in result.text_content
        assert result.confidence == 0.85


class TestOpenAIClientMessageTypeSelection:
    """Testes para seleção de tipo de mensagem."""

    @pytest.mark.asyncio
    async def test_select_message_type_text(self) -> None:
        """Verifica seleção de tipo texto."""
        client = OpenAIClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"message_type": "text", "parameters": {}, "confidence": 0.9, "rationale": "simple message"}'
                    }
                }
            ],
            "usage": {"total_tokens": 50}
        }
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_response
        client._http_client = mock_http

        request = MessageTypeSelectionRequest(
            text_content="Olá! Como posso ajudar?",
            options=[],
        )

        result = await client.select_message_type(request)

        assert result.message_type == "text"
        assert result.confidence == 0.9


class TestOpenAIClientClose:
    """Testes para fechamento do cliente."""

    @pytest.mark.asyncio
    async def test_close_client(self) -> None:
        """Verifica fechamento do cliente HTTP."""
        client = OpenAIClient(api_key="test-key")

        mock_http = AsyncMock()
        client._http_client = mock_http

        await client.close()

        mock_http.aclose.assert_called_once()
        assert client._http_client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self) -> None:
        """Verifica que close sem cliente não falha."""
        client = OpenAIClient(api_key="test-key")

        # Não deve lançar exceção
        await client.close()
