"""Router principal do WhatsApp — agrega todos os endpoints do canal."""

from __future__ import annotations

from fastapi import APIRouter

from api.routes.whatsapp.webhook import router as webhook_router

router = APIRouter()

# Webhook endpoints (GET para challenge, POST para eventos)
router.include_router(webhook_router)

# TODO: Adicionar outros endpoints conforme necessário
# - flows.py: endpoints de WhatsApp Flows
# - media.py: endpoints de upload de mídia (se exposto)
