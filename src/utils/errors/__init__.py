"""Exceções utilitárias compartilhadas."""

from .exceptions import (
    FirestoreUnavailableError,
    InfrastructureError,
    RedisConnectionError,
)

__all__ = [
    "FirestoreUnavailableError",
    "InfrastructureError",
    "RedisConnectionError",
]
