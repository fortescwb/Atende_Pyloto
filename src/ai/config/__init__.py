"""Configuração de IA.

Re-exporta loader institucional para uso externo.
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

__all__ = [
    "InstitutionalContextError",
    "clear_cache",
    "get_address_info",
    "get_business_hours",
    "get_contact_info",
    "get_institutional_prompt_section",
    "get_service_info",
    "load_institutional_context",
]
