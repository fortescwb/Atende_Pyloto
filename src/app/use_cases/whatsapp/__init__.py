"""Use cases específicos de WhatsApp."""

from .process_inbound_canonical import (
    InboundProcessingResult,
    ProcessInboundCanonicalUseCase,
)
from .send_outbound_message import SendOutboundMessageUseCase

__all__ = [
    # Use case canônico de inbound (pipeline 4 agentes)
    "InboundProcessingResult",
    "ProcessInboundCanonicalUseCase",
    # Outbound
    "SendOutboundMessageUseCase",
]
