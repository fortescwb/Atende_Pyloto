"""Extrator de payloads Email (SendGrid/Mailgun/IMAP).

Estrutura típica (SendGrid Inbound Parse):
- from, to, subject, text, html, attachments

Estrutura IMAP:
- email.message.Message object

TODO: Implementar quando canal Email for ativado.
"""

from __future__ import annotations

from typing import Any


def extract_payload_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai emails do payload para estrutura intermediária.

    TODO: Implementar extração específica Email.
    """
    _ = payload  # Placeholder
    return []
