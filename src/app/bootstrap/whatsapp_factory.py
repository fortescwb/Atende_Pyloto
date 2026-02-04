"""Factory de wiring para WhatsApp (bootstrap)."""

from __future__ import annotations

from typing import Any

from app.bootstrap.whatsapp_adapters import (
    GraphApiNormalizer,
    GraphApiOutboundSender,
    GraphApiOutboundValidator,
    GraphApiPayloadBuilder,
)
from app.coordinators.whatsapp.flows.sender import create_flow_sender
from app.use_cases.whatsapp.send_outbound_message import SendOutboundMessageUseCase


def create_whatsapp_outbound_use_case() -> SendOutboundMessageUseCase:
    """Cria use case outbound com dependências injetadas."""
    return SendOutboundMessageUseCase(
        validator=GraphApiOutboundValidator(),
        builder=GraphApiPayloadBuilder(),
        sender=GraphApiOutboundSender(),
    )


def create_whatsapp_outbound_sender() -> GraphApiOutboundSender:
    """Cria sender outbound direto (implementa OutboundSenderProtocol).

    Use para injetar em use cases que esperam OutboundSenderProtocol.
    """
    return GraphApiOutboundSender()


def create_whatsapp_normalizer() -> GraphApiNormalizer:
    """Cria normalizador inbound Graph API."""
    return GraphApiNormalizer()


def create_flow_sender_factory(
    private_key_pem: str,
    flow_endpoint_secret: str,
    passphrase: str | None = None,
):
    """Factory wrapper que cria uma implementação concreta de crypto e retorna
    um `FlowSender` configurado.

    A implementação concreta fica dentro de app.infra e é importada localmente
    para respeitar boundaries (wiring no bootstrap).
    """
    from app.infra.crypto import (
        decrypt_aes_key as infra_decrypt_aes_key,
    )
    from app.infra.crypto import (
        decrypt_flow_data as infra_decrypt_flow_data,
    )
    from app.infra.crypto import (
        encrypt_flow_response as infra_encrypt_flow_response,
    )
    from app.infra.crypto import (
        load_private_key as infra_load_private_key,
    )
    from app.infra.crypto import (
        validate_flow_signature as infra_validate_flow_signature,
    )

    class InfraCryptoAdapter:
        # Adapter leve que implementa FlowCryptoProtocol usando funções infra
        def load_private_key(self, private_key_pem: str, passphrase: str | None = None) -> Any:
            return infra_load_private_key(private_key_pem, passphrase)

        def decrypt_aes_key(self, private_key: Any, encrypted_aes_key: str) -> bytes:
            return infra_decrypt_aes_key(private_key, encrypted_aes_key)

        def decrypt_flow_data(
            self,
            aes_key: bytes,
            encrypted_flow_data: str,
            initial_vector: str,
        ) -> dict[str, Any]:
            return infra_decrypt_flow_data(aes_key, encrypted_flow_data, initial_vector)

        def encrypt_flow_response(
            self,
            response_data: dict[str, Any],
            aes_key: bytes | None = None,
        ) -> dict[str, str]:
            return infra_encrypt_flow_response(response_data, aes_key)

        def validate_flow_signature(self, payload: bytes, signature: str, secret: bytes) -> bool:
            return infra_validate_flow_signature(payload, signature, secret)

    crypto = InfraCryptoAdapter()
    return lambda: create_flow_sender(
        crypto=crypto,
        private_key_pem=private_key_pem,
        passphrase=passphrase,
        flow_endpoint_secret=flow_endpoint_secret,
    )


def create_process_inbound_canonical(
    *,
    normalizer,
    session_store,
    dedupe,
    ai_orchestrator,
    outbound_sender,
    audit_store: Any | None = None,
    conversation_store: Any | None = None,
    lead_profile_store: Any | None = None,
) -> Any:
    """Wiring para `ProcessInboundCanonicalUseCase` — injeta protocolos concretos.

    Args:
        normalizer: Normalizador de mensagens
        session_store: Store de sessão (Redis)
        dedupe: Serviço de dedupe
        ai_orchestrator: Orquestrador de IA
        outbound_sender: Sender outbound
        audit_store: Store de auditoria (opcional)
        conversation_store: Store de conversas permanente (Firestore, opcional)
        lead_profile_store: Store de LeadProfile (opcional, Redis/Memory)
    """
    from app.services.master_decider import MasterDecider
    from app.sessions.manager import SessionManager
    from app.use_cases.whatsapp.process_inbound_canonical import (
        ProcessInboundCanonicalUseCase,
    )

    session_manager = SessionManager(
        store=session_store,
        conversation_store=conversation_store,
    )
    master_decider = MasterDecider()

    return ProcessInboundCanonicalUseCase(
        normalizer=normalizer,
        session_manager=session_manager,
        dedupe=dedupe,
        ai_orchestrator=ai_orchestrator,
        outbound_sender=outbound_sender,
        audit_store=audit_store,
        master_decider=master_decider,
        lead_profile_store=lead_profile_store,
    )
