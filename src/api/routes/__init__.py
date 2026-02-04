"""Rotas HTTP da API — adapters de entrada por canal.

Responsabilidades:
- Definir endpoints HTTP (webhooks, health, admin)
- Validação inicial de request (headers, query params)
- Delegação para connectors/use_cases
- Respostas HTTP apropriadas

Estrutura por canal:
- routes/whatsapp/: endpoints WhatsApp
- routes/instagram/: endpoints Instagram
- routes/meta_shared/: endpoints compartilhados Meta
- routes/health/: health checks e readiness

Agregação:
- router.py: registra todos os routers no app principal
"""

from __future__ import annotations

from api.routes.router import create_api_router

__all__ = ["create_api_router"]
