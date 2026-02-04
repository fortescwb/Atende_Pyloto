"""Serviços de aplicação.

Unidades reutilizáveis de orquestração (sem IO direto).
Implementações concretas de IO ficam em app/infra/.
"""

from app.services.master_decider import MasterDecider, MasterDecision

__all__ = [
    "MasterDecider",
    "MasterDecision",
]
