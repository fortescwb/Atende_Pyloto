"""Exceções de domínio para falhas recuperáveis de infraestrutura."""

from __future__ import annotations


class InfrastructureError(RuntimeError):
    """Base para falhas de infraestrutura transitórias."""


class RedisConnectionError(InfrastructureError):
    """Falha de conexão/timeout ao acessar Redis."""


class FirestoreUnavailableError(InfrastructureError):
    """Falha de indisponibilidade ao acessar Firestore."""
