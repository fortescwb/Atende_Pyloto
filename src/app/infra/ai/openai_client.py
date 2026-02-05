"""Cliente OpenAI real para produção.

Implementa AIClientProtocol com chamadas reais à API OpenAI.
Implementação de IO — pertence a app/infra conforme REGRAS § 2.3.
Pipeline de 5 agentes conforme README.md.
"""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING

import httpx

from ai.models.contact_card_extraction import (
    ContactCardExtractionRequest,
    ContactCardExtractionResult,
    ContactCardPatch,
)
from ai.models.message_type_selection import (
    MessageTypeSelectionRequest,
    MessageTypeSelectionResult,
)
from ai.models.response_generation import (
    ResponseGenerationRequest,
    ResponseGenerationResult,
)
from ai.prompts import (
    CONTACT_CARD_EXTRACTOR_SYSTEM,
    DECISION_AGENT_SYSTEM,
    MESSAGE_TYPE_AGENT_SYSTEM,
    RESPONSE_AGENT_SYSTEM,
    STATE_AGENT_SYSTEM,
    format_contact_card_extractor_prompt,
    format_decision_agent_prompt,
    format_message_type_agent_prompt,
    format_response_agent_prompt,
    format_state_agent_prompt,
)
from ai.rules.fallbacks import (
    fallback_decision,
    fallback_message_type_selection,
    fallback_response_generation,
    fallback_state_suggestion,
)
from ai.utils.agent_parser import (
    parse_decision_agent_response,
    parse_response_candidates,
    parse_state_agent_response,
)
from app.infra.ai._openai_http import call_openai_api

if TYPE_CHECKING:
    from ai.config.settings import AISettings
    from ai.models.decision_agent import DecisionAgentRequest, DecisionAgentResult
    from ai.models.state_agent import StateAgentRequest, StateAgentResult

logger = logging.getLogger(__name__)

_AGENT_ROLE_MAP = {
    "state_agent": "STATE",
    "response_agent": "RESPONSE",
    "contact_card_extractor": "CONTACT_CARD_EXTRACTOR",
    "message_type_agent": "MESSAGE_TYPE",
    "decision_agent": "DECISION",
}


class OpenAIClient:
    """Cliente OpenAI para produção — Pipeline de 5 Agentes.

    Implementa AIClientProtocol com chamadas assíncronas à API.
    Usa httpx para requests async. Fallback seguro em caso de erro.

    Agentes:
    1. StateAgent - sugere próximos estados
    2. ResponseAgent - gera candidatos de resposta
    2-B. ContactCardExtractor - extrai dados para o contato
    3. MessageTypeAgent - seleciona tipo de mensagem
    4. DecisionAgent - consolida e decide
    """

    __slots__ = ("_api_key", "_http_client", "_settings")

    def __init__(
        self,
        settings: AISettings | None = None,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Inicializa cliente OpenAI."""
        from ai.config.settings import get_ai_settings

        self._settings = settings or get_ai_settings()
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._http_client = http_client

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Obtém ou cria cliente HTTP."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=self._settings.timeout.request_timeout,
            )
        return self._http_client

    async def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        agent_name: str,
    ) -> str | None:
        """Executa chamada à API OpenAI via helper."""
        from ai.config.settings import AgentRole

        model_settings = None
        role_name = _AGENT_ROLE_MAP.get(agent_name)
        if role_name:
            model_settings = self._settings.agents.get_for_agent(AgentRole[role_name])
        client = await self._get_http_client()
        return await call_openai_api(
            http_client=client,
            api_key=self._api_key,
            settings=self._settings,
            model_settings=model_settings,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            point_name=agent_name,
        )

    async def suggest_state(
        self,
        request: StateAgentRequest,
    ) -> StateAgentResult:
        """Sugere próximos estados usando StateAgent (LLM #1)."""
        user_prompt = format_state_agent_prompt(
            user_input=request.user_input,
            current_state=request.current_state,
            conversation_history=request.conversation_history,
            valid_transitions=request.valid_transitions,
        )
        raw_response = await self._call_openai(
            system_prompt=STATE_AGENT_SYSTEM,
            user_prompt=user_prompt,
            agent_name="state_agent",
        )
        if raw_response is None:
            return fallback_state_suggestion(
                request.current_state,
                request.valid_transitions,
                "openai_call_failed",
            )
        return parse_state_agent_response(
            raw_response,
            request.current_state,
            request.valid_transitions,
        )

    async def generate_response(
        self,
        request: ResponseGenerationRequest,
        conversation_history: str = "",
        contact_card: str = "",
        is_first_message: bool = False,
    ) -> ResponseGenerationResult:
        """Gera candidatos de resposta usando ResponseAgent (LLM #2)."""
        # Serializa session_context se for dict
        context_str = ""
        if request.session_context:
            if isinstance(request.session_context, dict):
                context_str = ", ".join(f"{k}={v}" for k, v in request.session_context.items())
            else:
                context_str = str(request.session_context)

        user_prompt = format_response_agent_prompt(
            user_input=request.user_input or "",
            current_state=request.current_state,
            detected_intent=request.detected_intent,
            next_state=request.next_state or request.current_state,
            session_context=context_str,
            conversation_history=conversation_history,
            contact_card=contact_card,
            is_first_message=is_first_message,
        )
        raw_response = await self._call_openai(
            system_prompt=RESPONSE_AGENT_SYSTEM,
            user_prompt=user_prompt,
            agent_name="response_agent",
        )
        if raw_response is None:
            return fallback_response_generation(reason="openai_call_failed")

        # Parseia candidatos e seleciona o melhor
        candidates = parse_response_candidates(raw_response)
        if not candidates:
            return fallback_response_generation(reason="no_candidates_parsed")

        best = max(candidates, key=lambda c: c.confidence)
        return ResponseGenerationResult(
            text_content=best.text_content,
            confidence=best.confidence,
            rationale=best.rationale,
        )

    async def select_message_type(
        self,
        request: MessageTypeSelectionRequest,
    ) -> MessageTypeSelectionResult:
        """Seleciona tipo de mensagem usando MessageTypeAgent (LLM #3)."""
        user_prompt = format_message_type_agent_prompt(
            text_content=request.text_content,
            options=request.options,
        )
        raw_response = await self._call_openai(
            system_prompt=MESSAGE_TYPE_AGENT_SYSTEM,
            user_prompt=user_prompt,
            agent_name="message_type_agent",
        )
        if raw_response is None:
            return fallback_message_type_selection(reason="openai_call_failed")

        # Parser simples - o message_type_agent retorna JSON direto
        from ai.utils._json_extractor import extract_json_from_response

        data = extract_json_from_response(raw_response)
        if data is None:
            return fallback_message_type_selection(reason="parse_error")

        return MessageTypeSelectionResult(
            message_type=str(data.get("message_type", "text")),
            confidence=float(data.get("confidence", 0.7)),
            rationale=data.get("rationale"),
        )

    async def make_decision(
        self,
        request: DecisionAgentRequest,
    ) -> DecisionAgentResult:
        """Consolida outputs e decide usando DecisionAgent (LLM #4)."""
        # Serializa outputs dos agentes anteriores para o prompt
        state_output = json.dumps({
            "current_state": request.state_result.current_state,
            "suggested_next_states": [
                {"state": s.state, "confidence": s.confidence}
                for s in request.state_result.suggested_next_states
            ],
            "confidence": request.state_result.confidence,
        }, ensure_ascii=False)

        response_output = json.dumps({
            "text_content": request.response_result.text_content,
            "confidence": request.response_result.confidence,
        }, ensure_ascii=False)

        message_type_output = json.dumps({
            "message_type": request.message_type_result.message_type,
            "confidence": request.message_type_result.confidence,
        }, ensure_ascii=False)

        user_prompt = format_decision_agent_prompt(
            state_agent_output=state_output,
            response_agent_output=response_output,
            message_type_agent_output=message_type_output,
            user_input=request.user_input,
            consecutive_low_confidence=request.consecutive_low_confidence,
        )

        raw_response = await self._call_openai(
            system_prompt=DECISION_AGENT_SYSTEM,
            user_prompt=user_prompt,
            agent_name="decision_agent",
        )
        if raw_response is None:
            return fallback_decision(
                request.consecutive_low_confidence,
                "openai_call_failed",
            )
        return parse_decision_agent_response(
            raw_response,
            request.consecutive_low_confidence,
        )

    async def extract_contact_card(
        self,
        request: ContactCardExtractionRequest,
    ) -> ContactCardExtractionResult:
        """Extrai dados do contato usando ContactCardExtractor (Agente 2-B)."""
        user_prompt = format_contact_card_extractor_prompt(
            user_message=request.user_message,
            contact_card=request.contact_card_summary,
            conversation_context="\n".join(request.conversation_context or []),
        )
        raw_response = await self._call_openai(
            system_prompt=CONTACT_CARD_EXTRACTOR_SYSTEM,
            user_prompt=user_prompt,
            agent_name="contact_card_extractor",
        )
        if raw_response is None:
            return ContactCardExtractionResult.empty()

        # Parser simples - retorna JSON direto
        from ai.utils._json_extractor import extract_json_from_response

        data = extract_json_from_response(raw_response)
        if data is None:
            return ContactCardExtractionResult.empty()

        updates = data.get("updates") if isinstance(data, dict) else {}
        try:
            patch = ContactCardPatch.model_validate(updates or {})
        except Exception:
            return ContactCardExtractionResult.empty()

        confidence = float(data.get("confidence", 0.0)) if isinstance(data, dict) else 0.0
        evidence = data.get("evidence") if isinstance(data.get("evidence"), list) else []

        return ContactCardExtractionResult(
            updates=patch,
            confidence=max(0.0, min(1.0, confidence)),
            evidence=evidence,
        )

    async def close(self) -> None:
        """Fecha cliente HTTP."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
