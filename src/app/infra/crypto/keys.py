"""Operações de chave RSA e AES para Flows."""

from __future__ import annotations

import base64
import binascii
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
    passphrase_bytes = passphrase.encode() if passphrase and passphrase.strip() else None

    def _load(password: bytes | None) -> Any:
        return serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=password,
            backend=default_backend(),
        )

    try:
        return _load(passphrase_bytes)
    except Exception as exc:
        # Permite fallback quando a chave não está criptografada, mas uma
        # passphrase foi injetada por configuração.
        exc_text = str(exc).lower()
        if passphrase_bytes and "private key is not encrypted" in exc_text:
            try:
                return _load(None)
            except Exception as retry_exc:
                raise FlowCryptoError(f"Invalid private key: {retry_exc}") from retry_exc
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
    def _decode_base64(value: str) -> bytes:
        normalized = value.strip()
        padded = normalized + ("=" * (-len(normalized) % 4))
        try:
            return base64.b64decode(padded, validate=True)
        except (ValueError, binascii.Error):
            return base64.urlsafe_b64decode(padded)

    try:
        aes_key_encrypted = _decode_base64(encrypted_aes_key)
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
    except (ValueError, binascii.Error) as exc:
        raise FlowCryptoError(f"Invalid base64 AES key: {exc}") from exc
    except Exception as exc:
        raise FlowCryptoError(f"AES key decryption failed: {exc}") from exc
