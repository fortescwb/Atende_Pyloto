"""Módulo de criptografia para WhatsApp Flows.

Este módulo contém a implementação de criptografia RSA/AES para
WhatsApp Flows (descriptografia de requests, criptografia de responses).

Localizado em app/infra/ para manter boundaries corretas:
- app/ não importa de api/ (exceto via bootstrap)
- Este módulo pode ser usado por coordinators em app/
"""

from .constants import AES_KEY_SIZE, IV_SIZE, TAG_SIZE
from .errors import FlowCryptoError
from .keys import decrypt_aes_key, load_private_key
from .payload import decrypt_flow_data, encrypt_flow_response
from .signature import validate_flow_signature

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
