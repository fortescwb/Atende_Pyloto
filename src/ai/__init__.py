"""Módulo AI do Atende Pyloto (arquitetura Otto).

Exporta contratos e serviços usados pelo agente único (Otto) e utilitários
determinísticos de suporte.
"""

# Config
from ai.config import AISettings, get_ai_settings

# Core protocols
from ai.core import ContactCardExtractorClientProtocol, OttoClientProtocol

# Models
from ai.models import (
    ContactCardExtractionRequest,
    ContactCardExtractionResult,
    ContactCardPatch,
    OttoDecision,
    OttoRequest,
)

# Rules
from ai.rules import (
    contains_disallowed_pii,
    contains_prohibited_promises,
    is_response_length_valid,
)

# Services
from ai.services import (
    ContactCardExtractorService,
    ContextInjector,
    DecisionValidatorService,
    OttoAgentService,
)

# Utils
from ai.utils import contains_pii, extract_json_from_response, mask_history, sanitize_pii

__all__ = [
    "AISettings",
    "ContactCardExtractionRequest",
    "ContactCardExtractionResult",
    "ContactCardExtractorClientProtocol",
    "ContactCardExtractorService",
    "ContactCardPatch",
    "ContextInjector",
    "DecisionValidatorService",
    "OttoAgentService",
    "OttoClientProtocol",
    "OttoDecision",
    "OttoRequest",
    "contains_disallowed_pii",
    "contains_pii",
    "contains_prohibited_promises",
    "extract_json_from_response",
    "get_ai_settings",
    "is_response_length_valid",
    "mask_history",
    "sanitize_pii",
]
