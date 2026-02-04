"""Erros de criptografia para WhatsApp Flows.

Definido em app/infra para manter boundaries corretas.
Usado por coordinators e pode ser re-exportado por api/connectors se necessário.
"""


class FlowCryptoError(Exception):
    """Erro em operação criptográfica de Flow."""

