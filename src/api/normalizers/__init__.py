"""Normalizers por canal — conversão de payloads externos para modelos internos.

Estrutura:
- meta_shared/: utilitários comuns para canais Meta (WhatsApp, Instagram, Facebook)
- whatsapp/: normalizer WhatsApp Business API
- instagram/: normalizer Instagram Messaging API
- facebook/: normalizer Facebook Messenger API

Cada canal tem seu próprio extractor e normalizer, mantendo SRP.
"""

# Exports do normalizer implementado (WhatsApp)
from .whatsapp import extract_messages, normalize_message, normalize_messages

__all__ = [
    "extract_messages",
    "normalize_message",
    "normalize_messages",
]
