"""Coordenação do fluxo inbound WhatsApp."""

from .handler import process_inbound_payload

__all__ = ["process_inbound_payload"]
