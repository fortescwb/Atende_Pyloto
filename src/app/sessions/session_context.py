"""Contexto institucional da sessão."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SessionContext:
    """Contexto institucional mínimo de uma sessão."""

    tenant_id: str = ""
    vertente: str = "geral"
    rules: dict[str, Any] = field(default_factory=dict)
    limits: dict[str, int] = field(default_factory=dict)
    prompt_vertical: str = ""
    prompt_contexts: list[str] = field(default_factory=list)
