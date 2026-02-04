"""Utilitários de IA.

Re-exporta parsers (4 agentes) e sanitizadores.
"""

from ai.utils._json_extractor import extract_json_from_response
from ai.utils.agent_parser import (
    parse_decision_agent_response,
    parse_response_candidates,
    parse_state_agent_response,
)
from ai.utils.sanitizer import contains_pii, mask_history, sanitize_pii

__all__ = [
    # Sanitizer
    "contains_pii",
    # JSON extractor
    "extract_json_from_response",
    "mask_history",
    "parse_decision_agent_response",
    "parse_response_candidates",
    # Agent parsers (4-agent pipeline)
    "parse_state_agent_response",
    "sanitize_pii",
]
