"""Normalizers por canal — conversão de payloads externos para modelos internos.

Estrutura:
- meta_shared/: utilitários comuns para canais Meta (WhatsApp, Instagram, Facebook)
- whatsapp/: normalizer WhatsApp Business API
- instagram/: normalizer Instagram Messaging API (TODO)
- facebook/: normalizer Facebook Messenger API (TODO)
- linkedin/: normalizer LinkedIn API (TODO)
- tiktok/: normalizer TikTok for Business API (TODO)
- youtube/: normalizer YouTube Data API (TODO)
- discord/: normalizer Discord Gateway API (TODO)
- google_calendar/: normalizer Google Calendar API (TODO)
- apple_calendar/: normalizer Apple Calendar/CalDAV (TODO)
- telegram/: normalizer Telegram Bot API (TODO)
- email/: normalizer Email SMTP/IMAP (TODO)
- sms/: normalizer SMS Twilio/Vonage (TODO)
- twitter/: normalizer Twitter/X API (TODO)

Cada canal tem seu próprio extractor e normalizer, mantendo SRP.
"""

# Exports do normalizer implementado (WhatsApp)
from .whatsapp import extract_messages, normalize_message, normalize_messages

__all__ = [
    "extract_messages",
    "normalize_message",
    "normalize_messages",
]

