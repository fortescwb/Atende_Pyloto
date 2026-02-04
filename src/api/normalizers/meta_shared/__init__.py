"""Utilitários compartilhados para normalizers Meta (WhatsApp, Instagram, Facebook).

Responsabilidades:
- Sanitização comum de payloads Meta
- Validação base de estrutura de mensagem
- Helpers reutilizáveis entre canais Meta Graph API
"""

from .sanitizer import sanitize_message_payload
from .validator import is_valid_message_data

__all__ = [
    "is_valid_message_data",
    "sanitize_message_payload",
]
