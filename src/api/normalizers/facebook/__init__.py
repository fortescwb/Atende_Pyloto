"""Normalizer Facebook Messenger — extração e normalização de mensagens.

Responsabilidades:
- Extrair mensagens do payload webhook Facebook Messenger API
- Normalizar para modelo interno NormalizedMessage
- Suportar: message, postback, referral, optin, delivery, read

Pendente: ativar quando canal Facebook for ativado.
"""

# from api.normalizers.meta_shared import is_valid_message_data, sanitize_message_payload

__all__: list[str] = []
