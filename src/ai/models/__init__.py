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
    # Decision Agent (LLM #4 - novo)
    "DecisionAgentRequest",
    "DecisionAgentResult",
    # Event Detection (LLM #1 legado - será substituído por StateAgent)
    "EventDetectionRequest",
    "EventDetectionResult",
    "MessageType",
    # Message Type Selection (LLM #3)
    "MessageTypeSelectionRequest",
    "MessageTypeSelectionResult",
    "ResponseCandidate",
    # Response Generation (LLM #2)
    "ResponseGenerationRequest",
    "ResponseGenerationResult",
    "ResponseOption",
    "ResponseTone",
    # State Agent (LLM #1 - novo)
    "StateAgentRequest",
    "StateAgentResult",
    "SuggestedState",
]
