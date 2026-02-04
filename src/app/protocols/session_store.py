"""Protocolos de domínio para persistência de sessão (sync e async)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SessionStoreProtocol(ABC):
    """Contrato mínimo síncrono para armazenamento de SessionState."""

    @abstractmethod
    def save(self, session: Any, ttl_seconds: int = 7200) -> None: ...

    @abstractmethod
    def load(self, session_id: str) -> Any | None: ...

    @abstractmethod
    def delete(self, session_id: str) -> bool: ...

    @abstractmethod
    def exists(self, session_id: str) -> bool: ...


class AsyncSessionStoreProtocol(ABC):
    """Contrato mínimo assíncrono para armazenamento de SessionState.

    Usa sufixo _async para evitar conflito de nomes quando classe
    implementa ambos protocolos (sync e async).
    """

    @abstractmethod
    async def save_async(self, session: Any, ttl_seconds: int = 7200) -> None: ...

    @abstractmethod
    async def load_async(self, session_id: str) -> Any | None: ...

    @abstractmethod
    async def delete_async(self, session_id: str) -> bool: ...

    @abstractmethod
    async def exists_async(self, session_id: str) -> bool: ...
