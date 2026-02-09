"""Bootstrap da aplicação — inicialização e wiring.

Este módulo é o composition root: configura logging, inicializa
dependências e conecta implementações concretas aos protocolos.

Uso:
    from app.bootstrap import initialize_app, get_session_store, get_dedupe_store

    # Na inicialização do serviço
    initialize_app()

    # Obter stores
    session_store = get_session_store()
    dedupe_store = get_dedupe_store()
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from app.observability import get_correlation_id
from config.logging import configure_logging
from config.settings import (
    get_firestore_settings,
    get_openai_settings,
    get_whatsapp_settings,
)

# Nome do serviço para logs e métricas
SERVICE_NAME = "atende_pyloto"

# Nível de log padrão (pode ser sobrescrito por env)
DEFAULT_LOG_LEVEL = "INFO"
STRICT_VALIDATION_ENVS = {"staging", "production"}

# Singletons de stores (lazy initialization)
_session_store = None
_dedupe_store = None
_audit_store = None

logger = logging.getLogger(__name__)


def initialize_app() -> None:
    """Inicializa a aplicação com todas as configurações necessárias.

    Deve ser chamada uma vez no início do serviço.

    Configura:
    - Logging estruturado JSON com correlation_id
    - Stores de sessão, dedupe e auditoria
    """
    log_level = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()

    configure_logging(
        level=log_level,
        service_name=SERVICE_NAME,
        correlation_id_getter=get_correlation_id,
    )


def initialize_test_app() -> None:
    """Inicializa a aplicação para testes.

    Configura logging em nível DEBUG sem JSON para facilitar debug.
    """
    configure_logging(
        level="DEBUG",
        service_name=f"{SERVICE_NAME}_test",
        correlation_id_getter=get_correlation_id,
    )


def validate_runtime_settings() -> None:
    """Valida settings obrigatórias no startup.

    Em `staging`/`production` falha rápido para impedir boot inválido.
    Em `development`/`test` mantém alerta sem bloquear execução local.
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    strict_mode = environment in STRICT_VALIDATION_ENVS
    errors: list[str] = []

    wa_errors = get_whatsapp_settings().validate()
    errors.extend(f"whatsapp: {error}" for error in wa_errors)

    openai_errors = get_openai_settings().validate()
    errors.extend(f"openai: {error}" for error in openai_errors)

    gcp_project = (
        os.getenv("GCP_PROJECT", "")
        or os.getenv("GOOGLE_CLOUD_PROJECT", "")
        or os.getenv("GCLOUD_PROJECT", "")
    )
    firestore_errors = get_firestore_settings().validate(gcp_project)
    errors.extend(f"firestore: {error}" for error in firestore_errors)

    if not errors:
        logger.info(
            "settings_validated",
            extra={"component": "bootstrap", "result": "ok", "environment": environment},
        )
        return

    logger.warning(
        "settings_validation_failed",
        extra={
            "component": "bootstrap",
            "result": "failed",
            "environment": environment,
            "error_count": len(errors),
            "errors": errors,
        },
    )
    if strict_mode:
        details = "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(f"Configuração inválida para {environment}:\n{details}")


# ──────────────────────────────────────────────────────────────────────────────
# Store Getters (lazy initialization com cache)
# ──────────────────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_session_store():
    """Obtém store de sessão (singleton).

    Returns:
        SessionStoreProtocol configurado conforme env
    """
    from app.bootstrap.dependencies import create_session_store
    return create_session_store()


@lru_cache(maxsize=1)
def get_dedupe_store():
    """Obtém store de dedupe (singleton).

    Returns:
        DedupeProtocol configurado conforme env
    """
    from app.bootstrap.dependencies import create_dedupe_store
    return create_dedupe_store()


@lru_cache(maxsize=1)
def get_audit_store():
    """Obtém store de auditoria (singleton).

    Returns:
        DecisionAuditStoreProtocol configurado conforme env
    """
    from app.bootstrap.dependencies import create_audit_store
    return create_audit_store()


@lru_cache(maxsize=1)
def get_async_session_store():
    """Obtém store de sessão assíncrono (singleton)."""
    from app.bootstrap.dependencies import create_async_session_store
    return create_async_session_store()


@lru_cache(maxsize=1)
def get_async_dedupe_store():
    """Obtém store de dedupe assíncrono (singleton)."""
    from app.bootstrap.dependencies import create_async_dedupe_store
    return create_async_dedupe_store()
