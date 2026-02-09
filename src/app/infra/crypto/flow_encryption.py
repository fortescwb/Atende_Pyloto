"""Criptografia para endpoint de WhatsApp Flows (data exchange)."""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.infra.crypto.errors import FlowCryptoError
from app.infra.crypto.keys import decrypt_aes_key, load_private_key


@dataclass(frozen=True, slots=True)
class DecryptedFlowRequest:
    """Payload descriptografado + material para resposta criptografada."""

    payload: dict[str, object]
    aes_key: bytes
    iv: bytes


def _decode_base64(raw_value: str) -> bytes:
    value = raw_value.strip()
    padded = value + ("=" * (-len(value) % 4))
    try:
        return base64.b64decode(padded, validate=True)
    except (ValueError, binascii.Error):
        # Be stricter before attempting urlsafe: only allow urlsafe chars
        # (alphanum, dash, underscore, padding). This prevents permissive
        # decoding of clearly invalid inputs like '%%%invalid'.
        import re

        if not re.fullmatch(r"[A-Za-z0-9_\-]+={0,2}", value):
            raise FlowCryptoError("Invalid base64 payload: invalid characters in input")
        try:
            return base64.urlsafe_b64decode(padded)
        except (ValueError, binascii.Error) as exc:
            raise FlowCryptoError(f"Invalid base64 payload: {exc}") from exc


def decrypt_flow_request(
    *,
    encrypted_flow_data_b64: str,
    encrypted_aes_key_b64: str,
    initial_vector_b64: str,
    private_key_pem: str,
    private_key_passphrase: str | None = None,
) -> DecryptedFlowRequest:
    """Descriptografa request do endpoint de Flow.

    O formato esperado pela Meta é:
    - `encrypted_aes_key`: chave AES criptografada com RSA-OAEP (base64)
    - `initial_vector`: IV AES-GCM (base64)
    - `encrypted_flow_data`: ciphertext + auth tag concatenados (base64)
    """
    iv = _decode_base64(initial_vector_b64)
    flow_data = _decode_base64(encrypted_flow_data_b64)

    # Validate AES key base64 before attempting to load private key to ensure
    # base64-related errors surface first (helps in debugging and testing).
    _ = _decode_base64(encrypted_aes_key_b64)

    private_key = load_private_key(private_key_pem, private_key_passphrase)
    aes_key = decrypt_aes_key(private_key, encrypted_aes_key_b64)

    try:
        aesgcm = AESGCM(aes_key)
        plaintext = aesgcm.decrypt(iv, flow_data, None)
        payload = json.loads(plaintext.decode("utf-8"))
    except Exception as exc:
        raise FlowCryptoError(f"Flow payload decryption failed: {exc}") from exc

    if not isinstance(payload, dict):
        raise FlowCryptoError("Flow payload must be a JSON object")

    return DecryptedFlowRequest(payload=payload, aes_key=aes_key, iv=iv)


def encrypt_flow_response(
    *,
    response: dict[str, object],
    aes_key: bytes,
    iv: bytes,
) -> str:
    """Criptografa resposta para Flow e retorna plaintext base64.

    A Meta espera a resposta criptografada com IV invertido (XOR 0xFF),
    retornada como texto simples contendo base64(ciphertext + tag).
    """
    if not isinstance(response, dict):
        raise FlowCryptoError("response must be a dict")

    try:
        flipped_iv = bytes(byte ^ 0xFF for byte in iv)
        plaintext = json.dumps(response, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        aesgcm = AESGCM(aes_key)
        encrypted = aesgcm.encrypt(flipped_iv, plaintext, None)
        return base64.b64encode(encrypted).decode("utf-8")
    except Exception as exc:
        raise FlowCryptoError(f"Flow response encryption failed: {exc}") from exc
