"""Agregador de settings de AI/LLM.

Re-exporta todas as settings de IA para uso externo.
"""

from __future__ import annotations

from config.settings.ai.flood import (
    FloodDetectionSettings,
    get_flood_detection_settings,
)
from config.settings.ai.openai import (
    OpenAISettings,
    get_openai_settings,
)

__all__ = [
    # Flood
    "FloodDetectionSettings",
    # OpenAI
    "OpenAISettings",
    "get_flood_detection_settings",
    "get_openai_settings",
]
