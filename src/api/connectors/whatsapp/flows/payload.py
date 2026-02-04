"""Criptografia de payloads para WhatsApp Flows."""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .constants import AES_KEY_SIZE, IV_SIZE, TAG_SIZE
from .errors import FlowCryptoError


def decrypt_flow_data(
    aes_key: bytes,
    encrypted_flow_data: str,
    initial_vector: str,
) -> dict[str, Any]:
    """Descriptografa dados de Flow com AES-256-GCM.

    Args:
        aes_key: Chave AES (256 bits)
        encrypted_flow_data: Dados criptografados (base64)
        initial_vector: IV para GCM (base64)

    Returns:
        Dicionário com dados descriptografados

    Raises:
        FlowCryptoError: Se decriptografia falhar
    """
    try:
        flow_data_encrypted = base64.b64decode(encrypted_flow_data)
        iv = base64.b64decode(initial_vector)

        aesgcm = AESGCM(aes_key)
        decrypted_bytes = aesgcm.decrypt(iv, flow_data_encrypted, None)
        return json.loads(decrypted_bytes.decode("utf-8"))

    except Exception as exc:
        raise FlowCryptoError(f"Flow data decryption failed: {exc}") from exc


def encrypt_flow_response(
    response_data: dict[str, Any],
    aes_key: bytes | None = None,
) -> dict[str, str]:
    """Criptografa resposta de Flow com AES-256-GCM.

    Args:
        response_data: Dados da resposta
        aes_key: Chave AES (gera nova se não fornecida)

    Returns:
        Dict com encrypted_response, iv, tag (todos base64)

    Raises:
        FlowCryptoError: Se criptografia falhar
    """
    try:
        if aes_key is None:
            aes_key = os.urandom(AES_KEY_SIZE)
        iv = os.urandom(IV_SIZE)

        plaintext = json.dumps(response_data).encode("utf-8")
        aesgcm = AESGCM(aes_key)
        ciphertext_with_tag = aesgcm.encrypt(iv, plaintext, None)

        ciphertext = ciphertext_with_tag[:-TAG_SIZE]
        tag = ciphertext_with_tag[-TAG_SIZE:]

        return {
            "encrypted_response": base64.b64encode(ciphertext).decode("utf-8"),
            "iv": base64.b64encode(iv).decode("utf-8"),
            "tag": base64.b64encode(tag).decode("utf-8"),
        }

    except Exception as exc:
        raise FlowCryptoError(f"Flow response encryption failed: {exc}") from exc
