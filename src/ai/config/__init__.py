"""Configuração de IA.

Re-exporta settings e loader institucional para uso externo.
"""

from ai.config.institutional_loader import (
    InstitutionalContextError,
    clear_cache,
    get_address_info,
    get_business_hours,
    get_contact_info,
    get_institutional_prompt_section,
    get_service_info,
    load_institutional_context,
)
from ai.config.settings import (
    DEFAULT_AI_SETTINGS,
    AgentModelConfig,
    AgentRole,
    AIModelSettings,
    AISettings,
    AIThresholdSettings,
    AITimeoutSettings,
    ReasoningLevel,
    get_ai_settings,
)

__all__ = [
    "DEFAULT_AI_SETTINGS",
    "AIModelSettings",
    "AISettings",
    "AIThresholdSettings",
    "AITimeoutSettings",
    "AgentModelConfig",
    "AgentRole",
    "InstitutionalContextError",
    "ReasoningLevel",
    "clear_cache",
    "get_address_info",
    "get_ai_settings",
    "get_business_hours",
    "get_contact_info",
    "get_institutional_prompt_section",
    "get_service_info",
    "load_institutional_context",
]
