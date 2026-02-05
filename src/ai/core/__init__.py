"""Core do módulo AI — protocolos utilizados pelos agentes ativos."""

from ai.core.contact_card_extractor_client import ContactCardExtractorClientProtocol
from ai.core.otto_client import OttoClientProtocol

__all__ = [
    "ContactCardExtractorClientProtocol",
    "OttoClientProtocol",
]
