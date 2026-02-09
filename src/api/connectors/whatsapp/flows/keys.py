"""Operações de chave RSA e AES para Flows."""

from __future__ import annotations

import base64
from typing import Any

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.hashes import SHA256

from .constants import AES_KEY_SIZES_ALLOWED
from .errors import FlowCryptoError


def load_private_key(private_key_pem: str, passphrase: str | None = None) -> Any:
    """Carrega chave privada RSA em formato PEM.

    Args:
        private_key_pem: Chave privada em formato PEM
        passphrase: Senha da chave (opcional)

    Returns:
        Objeto de chave privada RSA

    Raises:
        FlowCryptoError: Se chave inválida
    """
    try:
        passphrase_bytes = passphrase.encode() if passphrase else None
        return serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=passphrase_bytes,
            backend=default_backend(),
        )
    except Exception as exc:
        raise FlowCryptoError(f"Invalid private key: {exc}") from exc


def decrypt_aes_key(private_key: Any, encrypted_aes_key: str) -> bytes:
    """Descriptografa chave AES criptografada com RSA-OAEP.

    Args:
        private_key: Chave privada RSA
        encrypted_aes_key: Chave AES criptografada (base64)

    Returns:
        Chave AES bruta (128/192/256 bits)

    Raises:
        FlowCryptoError: Se decriptografia falhar
    """
    try:
        aes_key_encrypted = base64.b64decode(encrypted_aes_key)
        aes_key = private_key.decrypt(
            aes_key_encrypted,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=SHA256()),
                algorithm=SHA256(),
                label=None,
            ),
        )

        if len(aes_key) not in AES_KEY_SIZES_ALLOWED:
            msg = f"Invalid AES key size: {len(aes_key)}"
            raise FlowCryptoError(msg)

        return aes_key

    except FlowCryptoError:
        raise
    except Exception as exc:
        raise FlowCryptoError(f"AES key decryption failed: {exc}") from exc
