"""Protocolos para gerenciamento de sessão (SessionManager).

O use case deve depender desse protocolo em vez da implementação concreta.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class Session:
    session_id: str
    current_state: Any
    history: list[str]
    context: Any
    turn_count: int


class SessionManagerProtocol(Protocol):
    async def resolve_or_create(self, *, sender_id: str, tenant_id: str) -> Session:
        ...

    async def save(self, session: Session) -> None:
        ...

    async def close(self, session: Session, reason: str) -> None:
        ...
