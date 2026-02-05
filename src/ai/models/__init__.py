"""Modelos/DTOs para IA.

Re-exporta contratos de entrada/saída para os 4 pontos de LLM.
Conforme README.md: StateAgent (1), ResponseAgent (2), MessageTypeAgent (3),
DecisionAgent (4).
"""

from ai.models.decision_agent import (
    CONFIDENCE_THRESHOLD,
    ESCALATION_CONSECUTIVE_FAILURES,
    FALLBACK_RESPONSE,
    DecisionAgentRequest,
    DecisionAgentResult,
)
from ai.models.event_detection import EventDetectionRequest, EventDetectionResult
from ai.models.message_type_selection import (
    VALID_MESSAGE_TYPES,
    MessageType,
    MessageTypeSelectionRequest,
    MessageTypeSelectionResult,
)
from ai.models.otto import OttoDecision, OttoRequest
from ai.models.response_generation import (
    ResponseCandidate,
    ResponseGenerationRequest,
    ResponseGenerationResult,
    ResponseOption,
    ResponseTone,
)
from ai.models.state_agent import (
    StateAgentRequest,
    StateAgentResult,
    SuggestedState,
)

__all__ = [
    "CONFIDENCE_THRESHOLD",
    "ESCALATION_CONSECUTIVE_FAILURES",
    "FALLBACK_RESPONSE",
    "VALID_MESSAGE_TYPES",
    "DecisionAgentRequest",
    "DecisionAgentResult",
    "EventDetectionRequest",
    "EventDetectionResult",
    "MessageType",
    "MessageTypeSelectionRequest",
    "MessageTypeSelectionResult",
    "OttoDecision",
    "OttoRequest",
    "ResponseCandidate",
    "ResponseGenerationRequest",
    "ResponseGenerationResult",
    "ResponseOption",
    "ResponseTone",
    "StateAgentRequest",
    "StateAgentResult",
    "SuggestedState",
]
