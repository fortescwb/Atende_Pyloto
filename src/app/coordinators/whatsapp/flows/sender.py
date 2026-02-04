"""Coordenação de envio/recepção de WhatsApp Flows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.protocols.crypto import FlowCryptoError, FlowCryptoProtocol

from .models import DecryptedFlowData

logger = logging.getLogger(__name__)


class FlowSender:
    """Gerencia envio e recepção de WhatsApp Flows com criptografia.

    NOTE: agora depende de um objeto que implementa `FlowCryptoProtocol`, injetado
    via construtor — isso evita importar implementações concretas dentro do
    coordinator, respeitando as regras de boundary.
    """

    def __init__(
        self,
        *,
        crypto: FlowCryptoProtocol,
        private_key_pem: str,
        passphrase: str | None = None,
        flow_endpoint_secret: str,
    ) -> None:
        """Inicializa com dependência de crypto injetada.

        Args:
            crypto: implementação do protocolo de crypto
            private_key_pem: Chave privada RSA em formato PEM
            passphrase: Senha da chave privada (opcional)
            flow_endpoint_secret: Secret para validação de assinatura
        """
        self._crypto = crypto
        self._endpoint_secret = flow_endpoint_secret.encode("utf-8")
        try:
            self._private_key = self._crypto.load_private_key(private_key_pem, passphrase)
            logger.info("FlowSender initialized with RSA private key")
        except Exception as exc:
            # Envolver em FlowCryptoError do protocolo para comportamentos compatíveis
            logger.error("Failed to load RSA private key", extra={"error": str(exc)})
            raise FlowCryptoError(str(exc)) from exc
    def validate_signature(self, payload: bytes, signature: str) -> bool:
        """Valida assinatura HMAC-SHA256 do Meta."""
        is_valid = self._crypto.validate_flow_signature(payload, signature, self._endpoint_secret)
        if not is_valid:
            logger.warning("Signature validation failed")
        return is_valid

    def decrypt_request(
        self,
        encrypted_aes_key: str,
        encrypted_flow_data: str,
        initial_vector: str,
    ) -> DecryptedFlowData:
        """Descriptografa dados de Flow recebidos do Meta."""
        try:
            aes_key = self._crypto.decrypt_aes_key(self._private_key, encrypted_aes_key)
            data_dict = self._crypto.decrypt_flow_data(aes_key, encrypted_flow_data, initial_vector)

            logger.debug("Flow data decrypted successfully")

            return DecryptedFlowData(
                flow_token=data_dict.get("flow_token", ""),
                action=data_dict.get("action", ""),
                screen=data_dict.get("screen", ""),
                data=data_dict.get("data", {}),
                version=data_dict.get("version"),
            )

        except FlowCryptoError:
            raise
        except Exception as exc:
            logger.error("Flow decryption failed", extra={"error": str(exc)})
            raise FlowCryptoError(f"Decryption failed: {exc}") from exc

    def encrypt_response(
        self,
        response_data: dict[str, Any],
        aes_key: bytes | None = None,
    ) -> dict[str, str]:
        """Criptografa resposta de Flow."""
        try:
            result = self._crypto.encrypt_flow_response(response_data, aes_key)
            logger.debug("Flow response encrypted successfully")
            return result
        except FlowCryptoError:
            raise
        except Exception as exc:
            logger.error("Flow encryption failed", extra={"error": str(exc)})
            raise FlowCryptoError(f"Encryption failed: {exc}") from exc

    def health_check(self) -> dict[str, Any]:
        """Retorna status de health check para Meta."""
        return {
            "status": "healthy",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "version": "1.0",
        }


def create_flow_sender(
    *,
    crypto: FlowCryptoProtocol,
    private_key_pem: str,
    flow_endpoint_secret: str,
    passphrase: str | None = None,
) -> FlowSender:
    """Factory para FlowSender. Requer implementação de `FlowCryptoProtocol`.

    Nota: a criação da implementação concreta deve ser feita em `app.bootstrap`.
    """
    return FlowSender(
        crypto=crypto,
        private_key_pem=private_key_pem,
        passphrase=passphrase,
        flow_endpoint_secret=flow_endpoint_secret,
    )
