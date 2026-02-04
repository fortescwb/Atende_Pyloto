"""Serviços criptográficos e utilitários para WhatsApp Flows.

Este módulo re-exporta a implementação de app/infra/crypto para
manter compatibilidade com código existente em api/.

A implementação real está em app/infra/crypto/ para manter
boundaries corretas (app/ não importa api/).
"""

# Re-export from canonical location in app/infra/crypto
from app.infra.crypto import (
    AES_KEY_SIZE,
    IV_SIZE,
    TAG_SIZE,
    FlowCryptoError,
    decrypt_aes_key,
    decrypt_flow_data,
    encrypt_flow_response,
    load_private_key,
    validate_flow_signature,
)

__all__ = [
    "AES_KEY_SIZE",
    "IV_SIZE",
    "TAG_SIZE",
    "FlowCryptoError",
    "decrypt_aes_key",
    "decrypt_flow_data",
    "encrypt_flow_response",
    "load_private_key",
    "validate_flow_signature",
]
