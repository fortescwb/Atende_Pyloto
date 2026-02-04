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

import os
from functools import lru_cache

from app.observability import get_correlation_id
from config.logging import configure_logging

# Nome do serviço para logs e métricas
SERVICE_NAME = "atende_pyloto"

# Nível de log padrão (pode ser sobrescrito por env)
DEFAULT_LOG_LEVEL = "INFO"

# Singletons de stores (lazy initialization)
_session_store = None
_dedupe_store = None
_audit_store = None


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
