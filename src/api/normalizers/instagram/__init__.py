"""Normalizer Instagram — extração e normalização de mensagens DM e comentários.

Responsabilidades:
- Extrair mensagens do payload webhook Instagram Messaging API
- Normalizar para modelo interno NormalizedMessage
- Suportar: DM (text, attachments), story_reply, story_mention, postback

TODO: Implementar quando canal Instagram for ativado.
"""

# from api.normalizers.meta_shared import is_valid_message_data, sanitize_message_payload

__all__: list[str] = []
