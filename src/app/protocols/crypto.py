"""Protocolos para operações criptográficas usadas por Flows.

Definimos aqui a interface que a infra de crypto deve implementar. Isso permite
que coordenadores e use cases dependam de abstrações e não de implementações
concretas.
"""
from __future__ import annotations

from typing import Any, Protocol


class FlowCryptoError(Exception):
    """Erro genérico de crypto esperado pelos consumidores de protocolo."""


class FlowCryptoProtocol(Protocol):
    """Interface mínima esperada pela camada de aplicação para operações de Flow."""

    def load_private_key(self, private_key_pem: str, passphrase: str | None = None) -> Any:
        ...

    def decrypt_aes_key(self, private_key: Any, encrypted_aes_key: str) -> bytes:
        ...

    def decrypt_flow_data(
        self,
        aes_key: bytes,
        encrypted_flow_data: str,
        initial_vector: str,
    ) -> dict[str, Any]:
        ...

    def encrypt_flow_response(
        self,
        response_data: dict[str, Any],
        aes_key: bytes | None = None,
    ) -> dict[str, str]:
        ...

    def validate_flow_signature(self, payload: bytes, signature: str, secret: bytes) -> bool:
        ...
