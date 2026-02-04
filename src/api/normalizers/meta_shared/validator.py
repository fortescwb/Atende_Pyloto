"""Validação comum para payloads Meta Graph API.

Responsabilidades:
- Validar estrutura mínima de mensagem
- Verificar campos obrigatórios
- Rejeitar payloads malformados
"""

from __future__ import annotations

from typing import Any


def is_valid_message_data(message: dict[str, Any]) -> bool:
    """Valida shape mínimo necessário para seguir com normalização.

    Args:
        message: Payload extraído e sanitizado

    Returns:
        True se válido, False caso contrário
    """
    if not isinstance(message, dict):
        return False

    message_id = message.get("message_id")
    return bool(message_id)
