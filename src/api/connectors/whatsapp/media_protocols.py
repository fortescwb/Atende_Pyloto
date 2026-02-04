"""Protocolos e resultados para upload de mídia.

Responsabilidades:
- Contrato MediaMetadataStore (persistência de metadados)
- Dataclass MediaUploadResult

Conforme regras_e_padroes.md: SRP, <200 linhas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class MediaUploadResult:
    """Resultado de upload de mídia."""

    media_id: str | None
    gcs_uri: str
    sha256_hash: str
    size_bytes: int
    mime_type: str
    was_deduplicated: bool
    uploaded_at: datetime


class MediaMetadataStore(Protocol):
    """Contrato para persistência de metadados de mídia."""

    def get_by_hash(self, sha256_hash: str) -> MediaUploadResult | None:
        """Busca mídia por hash SHA256."""
        ...

    def save(self, result: MediaUploadResult) -> None:
        """Persiste metadados de mídia."""
        ...
