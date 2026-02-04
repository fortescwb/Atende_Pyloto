"""Cliente mock de IA para testes e desenvolvimento.

Retorna fallbacks determinísticos sem chamar LLM real.
Conforme REGRAS_E_PADROES.md § 2.1: ai/core contém interfaces e pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai.models.decision_agent import DecisionAgentRequest, DecisionAgentResult
from ai.models.event_detection import EventDetectionRequest, EventDetectionResult
from ai.models.lead_profile_extraction import (
    LeadProfileExtractionRequest,
    LeadProfileExtractionResult,
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

if TYPE_CHECKING:
    from ai.config.settings import AISettings


class MockAIClient:
    """Cliente mock de IA para testes e desenvolvimento.

    Retorna fallbacks determinísticos sem chamar LLM real.
    Implementa todos os métodos do AIClientProtocol.
    """

    def __init__(self, settings: AISettings | None = None) -> None:
        """Inicializa cliente mock."""
        from ai.config.settings import get_ai_settings

        self._settings = settings or get_ai_settings()

    async def detect_event(
        self,
        request: EventDetectionRequest,
    ) -> EventDetectionResult:
        """Retorna detecção mock baseada em heurísticas simples."""
        from ai.rules.fallbacks import get_fallback_confidence

        text_lower = request.user_input.lower()

        if any(word in text_lower for word in ["oi", "olá", "bom dia", "boa tarde"]):
            intent, confidence = "GREETING", 0.9
        elif any(word in text_lower for word in ["ajuda", "suporte", "problema"]):
            intent, confidence = "SUPPORT_REQUEST", 0.85
        elif any(word in text_lower for word in ["preço", "valor", "quanto"]):
            intent, confidence = "PRICING_INQUIRY", 0.8
        else:
            intent, confidence = "ENTRY_UNKNOWN", get_fallback_confidence()

        return EventDetectionResult(
            event="USER_SENT_TEXT",
            detected_intent=intent,
            confidence=confidence,
            requires_followup=confidence < 0.5,
            rationale="Mock: heurística baseada em keywords",
        )

    async def generate_response(
        self,
        request: ResponseGenerationRequest,
        conversation_history: str = "",
        lead_profile: str = "",
        is_first_message: bool = False,
    ) -> ResponseGenerationResult:
        """Retorna resposta mock genérica."""
        responses = {
            "GREETING": "Olá! Como posso ajudar você hoje?",
            "SUPPORT_REQUEST": "Entendo que precisa de ajuda. Pode me contar mais?",
            "PRICING_INQUIRY": "Para informações sobre valores, podemos agendar.",
        }
        text = responses.get(request.detected_intent, "Como posso ajudar?")

        return ResponseGenerationResult(
            text_content=text,
            confidence=0.8,
            rationale="Mock: resposta predefinida por intent",
        )

    async def select_message_type(
        self,
        request: MessageTypeSelectionRequest,
    ) -> MessageTypeSelectionResult:
        """Retorna seleção mock baseada em heurísticas."""
        if request.options and len(request.options) <= 3:
            return MessageTypeSelectionResult(
                message_type="interactive_button",
                confidence=0.9,
                rationale="Mock: opções presentes, usar botões",
            )
        return MessageTypeSelectionResult(
            message_type="text",
            confidence=0.85,
            rationale="Mock: sem opções, usar texto",
        )

    async def suggest_state(
        self,
        request: StateAgentRequest,
    ) -> StateAgentResult:
        """Retorna sugestão de estado mock baseada em heurísticas."""
        from ai.models.state_agent import SuggestedState

        current = request.current_state
        valid = request.valid_transitions
        text_lower = request.user_input.lower()

        if current == "INITIAL":
            next_state = "TRIAGE" if "TRIAGE" in valid else (valid[0] if valid else current)
            confidence = 0.85
        elif any(word in text_lower for word in ["ajuda", "suporte", "humano"]):
            next_state = "HANDOFF_HUMAN" if "HANDOFF_HUMAN" in valid else current
            confidence = 0.8
        elif any(word in text_lower for word in ["obrigado", "valeu", "blz"]):
            next_state = "SELF_SERVE_INFO" if "SELF_SERVE_INFO" in valid else current
            confidence = 0.75
        else:
            next_state = "COLLECTING_INFO" if "COLLECTING_INFO" in valid else current
            confidence = 0.7

        suggested = SuggestedState(
            state=next_state,
            confidence=confidence,
            reasoning="Mock: heurística baseada em keywords",
        )
        return StateAgentResult(
            previous_state=current,
            current_state=current,
            suggested_next_states=(suggested,),
            confidence=confidence,
            rationale="Mock: sugestão determinística por keywords",
        )

    async def make_decision(
        self,
        request: DecisionAgentRequest,
    ) -> DecisionAgentResult:
        """Retorna decisão final mock consolidando outputs anteriores."""
        from ai.models.decision_agent import CONFIDENCE_THRESHOLD, FALLBACK_RESPONSE

        # Calcula confiança combinada (média ponderada)
        combined_confidence = (
            request.state_result.confidence * 0.3
            + request.response_result.confidence * 0.4
            + request.message_type_result.confidence * 0.3
        )

        understood = combined_confidence >= CONFIDENCE_THRESHOLD
        should_escalate = request.consecutive_low_confidence >= 3
        final_text = request.response_result.text_content if understood else FALLBACK_RESPONSE

        if request.state_result.suggested_next_states:
            final_state = request.state_result.suggested_next_states[0].state
        else:
            final_state = request.state_result.current_state

        return DecisionAgentResult(
            final_state=final_state,
            final_text=final_text,
            final_message_type=request.message_type_result.message_type,
            understood=understood,
            confidence=combined_confidence,
            should_escalate=should_escalate,
            rationale="Mock: decisão baseada em média ponderada de confiança",
        )

    async def extract_lead_profile(
        self,
        request: LeadProfileExtractionRequest,
    ) -> LeadProfileExtractionResult:
        """Retorna extração mock de perfil de lead.

        Usa extração determinística por regex quando possível.
        """
        from ai.services.lead_extractor import extract_lead_data

        extracted = extract_lead_data(request.user_input)

        personal_data: dict[str, str] = {}
        if extracted.name:
            personal_data["name"] = extracted.name
        if extracted.email:
            personal_data["email"] = extracted.email

        return LeadProfileExtractionResult(
            personal_data=personal_data,
            personal_info_update=None,
            need=None,
            confidence=0.7 if personal_data else 0.5,
            raw_response="Mock: extração determinística por regex",
        )
