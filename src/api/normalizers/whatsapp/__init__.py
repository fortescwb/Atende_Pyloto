"""Normalizer WhatsApp — extração e normalização de mensagens.

Responsabilidades:
- Extrair mensagens do payload webhook WhatsApp Business API
- Normalizar para modelo interno NormalizedMessage
- Validar e sanitizar dados

Tipos suportados: text, image, video, audio, document, sticker,
location, address, contacts, interactive, reaction, button, order,
system, request_welcome, ephemeral.
"""

from .extractor import extract_payload_messages
from .normalizer import extract_messages, normalize_message, normalize_messages

__all__ = [
    "extract_messages",
    "extract_payload_messages",
    "normalize_message",
    "normalize_messages",
]
