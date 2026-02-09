"""Camada de compatibilidade para mixins do processamento inbound.

Mantém imports antigos apontando para os módulos especializados.
"""

from __future__ import annotations

from app.use_cases.whatsapp._inbound_processor_common import (
    _extract_contact_card_signals,
    _FallbackDecision,
)
from app.use_cases.whatsapp._inbound_processor_contact import InboundProcessorContactMixin
from app.use_cases.whatsapp._inbound_processor_context import (
    _AGENTS_PARALLEL_TIMEOUT_SECONDS,
    InboundProcessorContextMixin,
)
from app.use_cases.whatsapp._inbound_processor_dispatch import InboundProcessorDispatchMixin
from app.use_cases.whatsapp._inbound_processor_state_adjustments import (
    adjust_for_meeting_collected,
    adjust_for_meeting_question,
)

_adjust_for_meeting_collected = adjust_for_meeting_collected
_adjust_for_meeting_question = adjust_for_meeting_question

__all__ = [
    "_AGENTS_PARALLEL_TIMEOUT_SECONDS",
    "InboundProcessorContactMixin",
    "InboundProcessorContextMixin",
    "InboundProcessorDispatchMixin",
    "_FallbackDecision",
    "_adjust_for_meeting_collected",
    "_adjust_for_meeting_question",
    "_extract_contact_card_signals",
]
