"""Conector WhatsApp - adapter de borda para Meta Graph API.

Este módulo é o único ponto de IO para o canal WhatsApp.
Responsabilidades:
- Webhook (receive, verify, signature)
- HTTP client para Graph API
- Upload de mídia
- Modelos e erros do Graph API
- Criptografia de Flows
- Parsing de templates
- Cálculo de event_id para idempotência
"""

from .event_id import compute_inbound_event_id
from .http_client import WhatsAppHttpClient
from .meta_errors import WhatsAppApiError, is_permanent_error, parse_meta_error
from .signature import SignatureResult, verify_meta_signature

__all__ = [
    "SignatureResult",
    "WhatsAppApiError",
    "WhatsAppHttpClient",
    "compute_inbound_event_id",
    "is_permanent_error",
    "parse_meta_error",
    "verify_meta_signature",
]
