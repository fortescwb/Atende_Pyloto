"""Testes para criptografia do endpoint de WhatsApp Flow."""

from __future__ import annotations

import base64
import os

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256

from app.infra.crypto.errors import FlowCryptoError
from app.infra.crypto.flow_encryption import decrypt_flow_request, encrypt_flow_response


def _build_encrypted_request(payload: dict[str, object]) -> dict[str, object]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    aes_key = os.urandom(16)
    iv = os.urandom(12)

    plaintext = (
        b'{"action":"ping","flow_token":"tok","screen":"APPOINTMENT","data":{}}'
        if payload.get("action") == "ping"
        else str(payload).encode("utf-8")
    )
    if payload.get("action") == "ping":
        plaintext = (
            b'{"action":"ping","flow_token":"tok","screen":"APPOINTMENT","data":{},"version":"1"}'
        )
    else:
        import json

        plaintext = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    encrypted_flow_data = AESGCM(aes_key).encrypt(iv, plaintext, None)
    encrypted_aes_key = public_key.encrypt(
        aes_key,
        padding.OAEP(mgf=padding.MGF1(algorithm=SHA256()), algorithm=SHA256(), label=None),
    )
    return {
        "private_pem": private_pem,
        "aes_key": aes_key,
        "iv": iv,
        "encrypted_flow_data_b64": base64.b64encode(encrypted_flow_data).decode("utf-8"),
        "encrypted_aes_key_b64": base64.b64encode(encrypted_aes_key).decode("utf-8"),
        "initial_vector_b64": base64.b64encode(iv).decode("utf-8"),
    }


def test_decrypt_and_encrypt_roundtrip() -> None:
    encrypted = _build_encrypted_request(
        {"action": "ping", "flow_token": "tok", "screen": "APPOINTMENT", "data": {}, "version": "1"}
    )

    decrypted = decrypt_flow_request(
        encrypted_flow_data_b64=encrypted["encrypted_flow_data_b64"],  # type: ignore[arg-type]
        encrypted_aes_key_b64=encrypted["encrypted_aes_key_b64"],  # type: ignore[arg-type]
        initial_vector_b64=encrypted["initial_vector_b64"],  # type: ignore[arg-type]
        private_key_pem=encrypted["private_pem"],  # type: ignore[arg-type]
    )

    assert decrypted.payload["action"] == "ping"
    assert decrypted.aes_key == encrypted["aes_key"]  # type: ignore[comparison-overlap]
    assert decrypted.iv == encrypted["iv"]  # type: ignore[comparison-overlap]

    response_payload = {"data": {"status": "active"}}
    encrypted_response_b64 = encrypt_flow_response(
        response=response_payload,
        aes_key=decrypted.aes_key,
        iv=decrypted.iv,
    )
    encrypted_response = base64.b64decode(encrypted_response_b64)
    flipped_iv = bytes(byte ^ 0xFF for byte in decrypted.iv)
    plaintext = AESGCM(decrypted.aes_key).decrypt(flipped_iv, encrypted_response, None)
    assert plaintext == b'{"data":{"status":"active"}}'


def test_decrypt_flow_request_invalid_base64_raises() -> None:
    with pytest.raises(FlowCryptoError, match="Invalid base64 payload"):
        decrypt_flow_request(
            encrypted_flow_data_b64="%%%invalid",
            encrypted_aes_key_b64="also-invalid",
            initial_vector_b64="invalid",
            private_key_pem="invalid",
        )
