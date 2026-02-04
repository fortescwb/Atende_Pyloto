"""Settings do Google Cloud Storage.

Configurações para GCS buckets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class GCSSettings:
    """Configurações do Google Cloud Storage.

    Attributes:
        bucket_media: Bucket para mídia (imagens, vídeos, áudio)
        bucket_export: Bucket para exportações (relatórios, backups)
    """

    bucket_media: str = ""
    bucket_export: str = ""

    def validate(self) -> list[str]:
        """Valida configurações do GCS.

        Returns:
            Lista de erros de validação.
        """
        # Buckets são opcionais - só validamos se configurados
        # (podem não ser usados em todos os ambientes)
        return []


def _load_gcs_from_env() -> GCSSettings:
    """Carrega GCSSettings de variáveis de ambiente."""
    return GCSSettings(
        bucket_media=os.getenv("GCS_BUCKET_MEDIA", ""),
        bucket_export=os.getenv("GCS_BUCKET_EXPORT", ""),
    )


@lru_cache(maxsize=1)
def get_gcs_settings() -> GCSSettings:
    """Retorna instância cacheada de GCSSettings."""
    return _load_gcs_from_env()
