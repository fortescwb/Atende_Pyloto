"""Router principal do WhatsApp — agrega todos os endpoints do canal."""

from __future__ import annotations

from fastapi import APIRouter

from api.routes.whatsapp.flows import router as flows_router
from api.routes.whatsapp.webhook import router as webhook_router

router = APIRouter()

# Webhook endpoints (GET para challenge, POST para eventos)
router.include_router(webhook_router)
router.include_router(flows_router)

# TODO: Adicionar outros endpoints conforme necessário
# - media.py: endpoints de upload de mídia (se exposto)
