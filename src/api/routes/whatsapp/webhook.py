"""Endpoints de webhook do WhatsApp.

Endpoints:
- GET /webhook/whatsapp: verificação de webhook (Meta challenge)
- POST /webhook/whatsapp: recebimento de eventos inbound

Fluxo:
1. GET: Meta envia challenge, respondemos com hub.challenge
2. POST: Meta envia eventos, validamos assinatura, processamos

Segurança:
- Validação HMAC obrigatória em POST (exceto em dev sem secret)
- Resposta rápida (200 OK) para evitar retry do Meta
- Processamento pesado delegado para workers/filas
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Request, Response, status

from api.connectors.whatsapp.webhook.receive import (
    InvalidJsonError,
    InvalidSignatureError,
    parse_webhook_request,
)
from api.connectors.whatsapp.webhook.verify import (
    WebhookChallengeError,
    verify_webhook_challenge,
)
from app.coordinators.whatsapp.inbound.handler import process_inbound_payload
from app.observability import get_correlation_id, reset_correlation_id, set_correlation_id
from config.settings import get_whatsapp_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy-loaded use case (inicializado na primeira requisição)
_inbound_use_case = None
_background_tasks: set[asyncio.Task] = set()


def _get_inbound_use_case():
    """Obtém o use case de processamento inbound (lazy-loading)."""
    global _inbound_use_case
    if _inbound_use_case is None:
        from app.bootstrap.dependencies import (
            create_async_dedupe_store,
            create_async_session_store,
            create_contact_card_extractor_service,
            create_contact_card_store,
            create_otto_agent_service,
            create_transcription_service,
        )
        from app.bootstrap.whatsapp_factory import (
            create_process_inbound_canonical,
            create_whatsapp_normalizer,
            create_whatsapp_outbound_sender,
        )

        _inbound_use_case = create_process_inbound_canonical(
            normalizer=create_whatsapp_normalizer(),
            session_store=create_async_session_store(),
            dedupe=create_async_dedupe_store(),
            otto_agent=create_otto_agent_service(),
            outbound_sender=create_whatsapp_outbound_sender(),
            contact_card_store=create_contact_card_store(),
            transcription_service=create_transcription_service(),
            contact_card_extractor=create_contact_card_extractor_service(),
        )
    return _inbound_use_case


async def _process_inbound_payload_safe(
    *,
    payload: dict[str, Any],
    correlation_id: str,
    use_case: Any,
    tenant_id: str,
) -> None:
    """Executa processamento inbound em background sem propagar exceções."""
    try:
        await process_inbound_payload(
            payload=payload,
            correlation_id=correlation_id,
            use_case=use_case,
            tenant_id=tenant_id,
        )
    except Exception:
        logger.exception(
            "webhook_processing_failed",
            extra={
                "channel": "whatsapp",
                "correlation_id": correlation_id,
            },
        )


@router.get("/")
async def verify_webhook(request: Request) -> Response:
    """Verificação de webhook — responde ao challenge da Meta.

    Query params esperados:
    - hub.mode: deve ser "subscribe"
    - hub.verify_token: deve corresponder ao configurado
    - hub.challenge: valor a retornar

    Returns:
        Texto do challenge ou erro 403.
    """
    settings = get_whatsapp_settings()

    hub_mode = request.query_params.get("hub.mode")
    hub_verify_token = request.query_params.get("hub.verify_token")
    hub_challenge = request.query_params.get("hub.challenge")

    try:
        challenge = verify_webhook_challenge(
            hub_mode=hub_mode,
            hub_verify_token=hub_verify_token,
            hub_challenge=hub_challenge,
            expected_token=settings.verify_token,
        )

        logger.info(
            "webhook_verified",
            extra={
                "channel": "whatsapp",
                "hub_mode": hub_mode,
            },
        )

        # Meta espera o challenge como texto puro
        return Response(
            content=challenge,
            media_type="text/plain",
            status_code=status.HTTP_200_OK,
        )

    except WebhookChallengeError as exc:
        logger.warning(
            "webhook_verification_failed",
            extra={
                "channel": "whatsapp",
                "error": str(exc),
            },
        )
        return Response(
            content="Forbidden",
            media_type="text/plain",
            status_code=status.HTTP_403_FORBIDDEN,
        )


@router.post("/", response_model=None)
async def receive_webhook(request: Request) -> Response | dict[str, Any]:
    """Recebimento de eventos inbound do WhatsApp.

    Validações:
    1. Assinatura HMAC (X-Hub-Signature-256)
    2. JSON válido
    3. Estrutura básica do payload

    Processamento:
    - Responde 200 OK imediatamente
    - TODO: Enfileira para processamento assíncrono

    Returns:
        Confirmação de recebimento ou Response de erro.
    """
    # Configura correlation_id para rastreamento
    correlation_id = request.headers.get("x-correlation-id")
    token = set_correlation_id(correlation_id)

    try:
        settings = get_whatsapp_settings()

        # Lê body bruto para validação de assinatura
        raw_body = await request.body()

        # Headers como dict simples
        headers = dict(request.headers)

        try:
            _payload, signature_result = parse_webhook_request(
                raw_body=raw_body,
                headers=headers,
                secret=settings.webhook_secret or None,
            )

            logger.info(
                "webhook_received",
                extra={
                    "channel": "whatsapp",
                    "correlation_id": get_correlation_id(),
                    "signature_valid": signature_result.valid,
                    "signature_skipped": signature_result.skipped,
                    "payload_size": len(raw_body),
                },
            )

            # Processa o payload de forma assíncrona (fire-and-forget)
            # Responde 200 OK imediatamente para o Meta
            use_case = _get_inbound_use_case()
            if use_case is not None:
                task = asyncio.create_task(
                    _process_inbound_payload_safe(
                        payload=_payload,
                        correlation_id=get_correlation_id(),
                        use_case=use_case,
                        tenant_id="default",
                    )
                )
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)
                logger.info(
                    "webhook_processing_scheduled",
                    extra={
                        "channel": "whatsapp",
                        "correlation_id": get_correlation_id(),
                    },
                )
            else:
                logger.warning(
                    "webhook_use_case_unavailable",
                    extra={
                        "channel": "whatsapp",
                        "correlation_id": get_correlation_id(),
                        "reason": "ProcessInboundCanonicalUseCase could not be initialized",
                    },
                )

            return {
                "status": "received",
                "correlation_id": get_correlation_id(),
            }

        except InvalidSignatureError as exc:
            logger.warning(
                "webhook_signature_invalid",
                extra={
                    "channel": "whatsapp",
                    "correlation_id": get_correlation_id(),
                    "error": str(exc),
                },
            )
            return Response(
                content="Unauthorized",
                media_type="text/plain",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        except InvalidJsonError as exc:
            logger.warning(
                "webhook_json_invalid",
                extra={
                    "channel": "whatsapp",
                    "correlation_id": get_correlation_id(),
                    "error": str(exc),
                },
            )
            return Response(
                content="Bad Request",
                media_type="text/plain",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    finally:
        reset_correlation_id(token)
