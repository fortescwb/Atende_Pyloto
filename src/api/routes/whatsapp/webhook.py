"""Endpoints de webhook do WhatsApp."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from api.connectors.whatsapp.webhook.receive import (
    InvalidJsonError,
    InvalidSignatureError,
    parse_webhook_request,
)
from api.connectors.whatsapp.webhook.verify import (
    WebhookChallengeError,
    verify_webhook_challenge,
)
from api.routes.whatsapp.webhook_runtime import dispatch_inbound_processing
from app.observability import get_correlation_id, reset_correlation_id, set_correlation_id
from config.settings import get_whatsapp_settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def verify_webhook(request: Request) -> Response:
    """Verificação de webhook — responde ao challenge da Meta."""
    settings = get_whatsapp_settings()
    try:
        challenge = verify_webhook_challenge(
            hub_mode=request.query_params.get("hub.mode"),
            hub_verify_token=request.query_params.get("hub.verify_token"),
            hub_challenge=request.query_params.get("hub.challenge"),
            expected_token=settings.verify_token,
        )
        logger.info(
            "webhook_verified",
            extra={"channel": "whatsapp", "hub_mode": request.query_params.get("hub.mode")},
        )
        return Response(
            content=challenge,
            media_type="text/plain",
            status_code=status.HTTP_200_OK,
        )
    except WebhookChallengeError as exc:
        logger.warning(
            "webhook_verification_failed",
            extra={"channel": "whatsapp", "error": str(exc)},
        )
        return Response(
            content="Forbidden",
            media_type="text/plain",
            status_code=status.HTTP_403_FORBIDDEN,
        )


@router.post("/", response_model=None)
async def receive_webhook(request: Request) -> Response | dict[str, Any]:
    """Recebimento de eventos inbound do WhatsApp."""
    token = set_correlation_id(request.headers.get("x-correlation-id"))
    try:
        settings = get_whatsapp_settings()
        try:
            payload, correlation_id = await _parse_and_log_request(request, settings)
            await dispatch_inbound_processing(
                payload=payload,
                correlation_id=correlation_id,
                settings=settings,
                tenant_id="default",
            )
            return {"status": "received", "correlation_id": correlation_id}
        except InvalidSignatureError as exc:
            return _error_response("webhook_signature_invalid", "Unauthorized", 401, str(exc))
        except InvalidJsonError as exc:
            return _error_response("webhook_json_invalid", "Bad Request", 400, str(exc))
        except Exception:
            correlation_id = get_correlation_id()
            logger.exception(
                "webhook_dispatch_failed",
                extra={
                    "channel": "whatsapp",
                    "correlation_id": correlation_id,
                },
            )
            return JSONResponse(
                content={
                    "error": "internal_error",
                    "message": "Failed to process inbound payload",
                    "correlation_id": correlation_id,
                },
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    finally:
        reset_correlation_id(token)


async def _parse_and_log_request(request: Request, settings: Any) -> tuple[dict[str, Any], str]:
    raw_body = await request.body()
    payload, signature_result = parse_webhook_request(
        raw_body=raw_body,
        headers=dict(request.headers),
        secret=settings.webhook_secret or None,
    )
    correlation_id = get_correlation_id()
    logger.info(
        "webhook_received",
        extra={
            "channel": "whatsapp",
            "correlation_id": correlation_id,
            "signature_valid": signature_result.valid,
            "signature_skipped": signature_result.skipped,
            "payload_size": len(raw_body),
        },
    )
    return payload, correlation_id


def _error_response(
    event: str,
    content: str,
    status_code: int,
    error: str,
) -> Response:
    logger.warning(
        event,
        extra={
            "channel": "whatsapp",
            "correlation_id": get_correlation_id(),
            "error": error,
        },
    )
    return Response(
        content=content,
        media_type="text/plain",
        status_code=status_code,
    )
