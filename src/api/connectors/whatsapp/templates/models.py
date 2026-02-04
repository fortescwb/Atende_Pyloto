"""Modelos de template WhatsApp."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


class TemplateCategory(str, Enum):
    """Categorias de template conforme Meta."""

    MARKETING = "MARKETING"
    UTILITY = "UTILITY"
    AUTHENTICATION = "AUTHENTICATION"


class TemplateStatus(str, Enum):
    """Status de aprovação de template."""

    APPROVED = "APPROVED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class TemplateParameter:
    """Parâmetro de template."""

    type: str
    index: int


@dataclass
class TemplateMetadata:
    """Metadados de template do WhatsApp."""

    name: str
    namespace: str
    language: str
    category: TemplateCategory
    status: TemplateStatus
    components: list[dict]
    parameters: list[TemplateParameter] = field(default_factory=list)
    last_synced_at: datetime | None = None
