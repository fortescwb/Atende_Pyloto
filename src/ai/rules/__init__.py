"""Regras determinísticas para IA.

Re-exporta fallbacks e funções de decisão.
"""

from ai.rules.fallbacks import (
    fallback_decision,
    fallback_event_detection,
    fallback_message_type_selection,
    fallback_response_generation,
    fallback_state_suggestion,
    get_fallback_confidence,
    is_confidence_acceptable,
    should_require_human_review,
)

__all__ = [
    "fallback_decision",
    "fallback_event_detection",
    "fallback_message_type_selection",
    "fallback_response_generation",
    "fallback_state_suggestion",
    "get_fallback_confidence",
    "is_confidence_acceptable",
    "should_require_human_review",
]
