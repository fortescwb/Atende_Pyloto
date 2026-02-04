"""Builders de payload para API Meta/WhatsApp.

Este pacote contém builders especializados por tipo de mensagem,
separando responsabilidades conforme regras_e_padroes.md.
"""

from api.payload_builders.whatsapp.base import (
    PayloadBuilder,
    build_base_payload,
)
from api.payload_builders.whatsapp.factory import (
    get_payload_builder,
)

__all__ = [
    "PayloadBuilder",
    "build_base_payload",
    "get_payload_builder",
]
