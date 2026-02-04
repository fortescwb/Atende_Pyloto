"""Módulo AI do Atende Pyloto.

Implementa pipeline de 4 agentes LLM para processamento de mensagens:
1. StateAgent - identifica estado e sugere transições FSM
2. ResponseAgent - gera candidatos de resposta
3. MessageTypeAgent - seleciona formato da mensagem
4. DecisionAgent - valida e consolida decisão final

Conforme AUDITORIA_ARQUITETURA.md § 10 e README.md.
"""

# Config
from ai.config import AISettings, get_ai_settings

# Core
from ai.core import AIClientProtocol, MockAIClient

# Models — mantidos para compatibilidade de tipos
from ai.models import (
    DecisionAgentRequest,
    DecisionAgentResult,
    MessageTypeSelectionRequest,
    MessageTypeSelectionResult,
    ResponseGenerationRequest,
    ResponseGenerationResult,
    StateAgentRequest,
    StateAgentResult,
)

# Rules
from ai.rules import (
    fallback_decision,
    fallback_message_type_selection,
    fallback_response_generation,
    fallback_state_suggestion,
    get_fallback_confidence,
    is_confidence_acceptable,
    should_require_human_review,
)

# Services
from ai.services import AIOrchestrator, OrchestratorResult

# Utils
from ai.utils import (
    contains_pii,
    extract_json_from_response,
    mask_history,
    parse_decision_agent_response,
    parse_response_candidates,
    parse_state_agent_response,
    sanitize_pii,
)

__all__ = [
    # Core
    "AIClientProtocol",
    # Services
    "AIOrchestrator",
    # Config
    "AISettings",
    "DecisionAgentRequest",
    "DecisionAgentResult",
    "MessageTypeSelectionRequest",
    "MessageTypeSelectionResult",
    "MockAIClient",
    "OrchestratorResult",
    "ResponseGenerationRequest",
    "ResponseGenerationResult",
    # Models
    "StateAgentRequest",
    "StateAgentResult",
    "contains_pii",
    # Utils
    "extract_json_from_response",
    "fallback_decision",
    "fallback_message_type_selection",
    "fallback_response_generation",
    # Rules
    "fallback_state_suggestion",
    "get_ai_settings",
    "get_fallback_confidence",
    "is_confidence_acceptable",
    "mask_history",
    "parse_decision_agent_response",
    "parse_response_candidates",
    "parse_state_agent_response",
    "sanitize_pii",
    "should_require_human_review",
]
