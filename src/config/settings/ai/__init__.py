"""Agregador de settings de AI/LLM.

Re-exporta todas as settings de IA para uso externo.
"""

from __future__ import annotations

from config.settings.ai.flood import (
    FloodDetectionSettings,
    get_flood_detection_settings,
)
from config.settings.ai.llm_phases import (
    AuditBackend,
    MasterDeciderSettings,
    ResponseGeneratorSettings,
    StateSelectorSettings,
    get_master_decider_settings,
    get_response_generator_settings,
    get_state_selector_settings,
)
from config.settings.ai.openai import (
    OpenAISettings,
    get_openai_settings,
)

__all__ = [
    # Types
    "AuditBackend",
    # Flood
    "FloodDetectionSettings",
    "MasterDeciderSettings",
    # OpenAI
    "OpenAISettings",
    "ResponseGeneratorSettings",
    # LLM Phases
    "StateSelectorSettings",
    "get_flood_detection_settings",
    "get_master_decider_settings",
    "get_openai_settings",
    "get_response_generator_settings",
    "get_state_selector_settings",
]
