"""Configuração de IA.

Re-exporta settings para uso externo.
"""

from ai.config.settings import (
    DEFAULT_AI_SETTINGS,
    AIModelSettings,
    AISettings,
    AIThresholdSettings,
    AITimeoutSettings,
    get_ai_settings,
)

__all__ = [
    "DEFAULT_AI_SETTINGS",
    "AIModelSettings",
    "AISettings",
    "AIThresholdSettings",
    "AITimeoutSettings",
    "get_ai_settings",
]
