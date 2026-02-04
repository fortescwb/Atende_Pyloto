"""Settings do Cloud Tasks.

Configurações para Google Cloud Tasks (filas de processamento).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

QueueBackend = Literal["memory", "cloud_tasks"]


@dataclass(frozen=True)
class CloudTasksSettings:
    """Configurações do Cloud Tasks.

    Attributes:
        backend: Backend para filas (memory|cloud_tasks)
        project_id: ID do projeto GCP
        location: Região das filas
        queue_outbound: Nome da fila de mensagens outbound
        queue_webhook: Nome da fila de webhooks
    """

    backend: QueueBackend = "memory"
    project_id: str = ""
    location: str = "us-central1"
    queue_outbound: str = "whatsapp-outbound"
    queue_webhook: str = "webhook-processing"

    def validate(self, gcp_project: str, is_development: bool) -> list[str]:
        """Valida configurações do Cloud Tasks.

        Args:
            gcp_project: Projeto GCP padrão.
            is_development: Se está em ambiente de desenvolvimento.

        Returns:
            Lista de erros de validação.
        """
        errors: list[str] = []
        valid_backends = {"memory", "cloud_tasks"}

        if self.backend not in valid_backends:
            errors.append(f"QUEUE_BACKEND inválido: {self.backend}")

        if self.backend == "memory" and not is_development:
            errors.append(
                "QUEUE_BACKEND=memory proibido em staging/production. "
                "Use cloud_tasks."
            )

        if self.backend == "cloud_tasks":
            effective_project = self.project_id or gcp_project
            if not effective_project:
                errors.append(
                    "QUEUE_BACKEND=cloud_tasks requer "
                    "CLOUD_TASKS_PROJECT_ID ou GCP_PROJECT"
                )

            if not self.location:
                errors.append("CLOUD_TASKS_LOCATION não pode ser vazio")

        return errors


def _load_cloud_tasks_from_env() -> CloudTasksSettings:
    """Carrega CloudTasksSettings de variáveis de ambiente."""
    backend_str = os.getenv("QUEUE_BACKEND", "memory").lower()
    backend: QueueBackend = backend_str if backend_str == "cloud_tasks" else "memory"

    return CloudTasksSettings(
        backend=backend,
        project_id=os.getenv("CLOUD_TASKS_PROJECT_ID", ""),
        location=os.getenv("CLOUD_TASKS_LOCATION", "us-central1"),
        queue_outbound=os.getenv("CLOUD_TASKS_QUEUE_OUTBOUND", "whatsapp-outbound"),
        queue_webhook=os.getenv("CLOUD_TASKS_QUEUE_WEBHOOK", "webhook-processing"),
    )


@lru_cache(maxsize=1)
def get_cloud_tasks_settings() -> CloudTasksSettings:
    """Retorna instância cacheada de CloudTasksSettings."""
    return _load_cloud_tasks_from_env()
