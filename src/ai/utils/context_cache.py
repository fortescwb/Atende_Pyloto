"""Cache inteligente para contextos YAML (P2-1).

Reduz I/O repetido carregando YAMLs em memória com TTL e invalidação manual.
Thread-safe para uso em ambiente assíncrono/concorrente.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Cache global com lock para thread-safety
_cache: dict[str, dict[str, Any]] = {}
_cache_timestamps: dict[str, float] = {}
_cache_lock = threading.Lock()

# Configuração padrão
DEFAULT_TTL_SECONDS = 300  # 5 minutos
_enabled = True


def enable_cache() -> None:
    """Ativa cache (padrão já é ativo)."""
    global _enabled
    _enabled = True


def disable_cache() -> None:
    """Desativa cache (útil para testes)."""
    global _enabled
    _enabled = False


def clear_cache() -> None:
    """Limpa todo o cache manualmente."""
    with _cache_lock:
        count = len(_cache)
        _cache.clear()
        _cache_timestamps.clear()
        logger.info(
            "context_cache_cleared",
            extra={
                "component": "context_cache",
                "action": "clear",
                "result": "ok",
                "items_cleared": count,
            },
        )


def invalidate_key(key: str) -> None:
    """Invalida entrada específica do cache."""
    with _cache_lock:
        if key in _cache:
            del _cache[key]
            del _cache_timestamps[key]
            logger.debug(
                "context_cache_invalidated",
                extra={
                    "component": "context_cache",
                    "action": "invalidate",
                    "result": "ok",
                    "key": key,
                },
            )


def get_cache_stats() -> dict[str, int]:
    """Retorna estatísticas do cache (útil para debug/monitoramento)."""
    with _cache_lock:
        return {
            "total_entries": len(_cache),
            "total_size_bytes": sum(len(str(v)) for v in _cache.values()),
        }


def load_yaml_cached(
    path: Path,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> dict[str, Any]:
    """Carrega YAML do cache ou filesystem.

    Args:
        path: Caminho absoluto do arquivo YAML
        ttl_seconds: Time-to-live em segundos (padrão 300s)

    Returns:
        Dict com conteúdo do YAML ou {} se inválido/não encontrado

    Notas:
        - Thread-safe usando lock
        - Cache hit/miss registrado em logs estruturados
        - TTL automático invalida entradas antigas
    """
    if not _enabled:
        return _load_yaml_from_disk(path)

    cache_key = str(path.resolve())
    now = time.time()

    with _cache_lock:
        # Verifica cache hit com TTL
        if cache_key in _cache:
            timestamp = _cache_timestamps[cache_key]
            if now - timestamp < ttl_seconds:
                logger.debug(
                    "context_cache_hit",
                    extra={
                        "component": "context_cache",
                        "action": "load",
                        "result": "hit",
                        "key": cache_key,
                        "age_seconds": round(now - timestamp, 2),
                    },
                )
                return _cache[cache_key].copy()  # retorna cópia para segurança

            # TTL expirado, remove entrada
            del _cache[cache_key]
            del _cache_timestamps[cache_key]
            logger.debug(
                "context_cache_expired",
                extra={
                    "component": "context_cache",
                    "action": "load",
                    "result": "expired",
                    "key": cache_key,
                    "age_seconds": round(now - timestamp, 2),
                },
            )

        # Cache miss - carrega do disco
        data = _load_yaml_from_disk(path)
        _cache[cache_key] = data
        _cache_timestamps[cache_key] = now

        logger.debug(
            "context_cache_miss",
            extra={
                "component": "context_cache",
                "action": "load",
                "result": "miss",
                "key": cache_key,
            },
        )

        return data.copy()


def _load_yaml_from_disk(path: Path) -> dict[str, Any]:
    """Helper interno para carregar YAML do filesystem."""
    try:
        if not path.exists():
            logger.warning(
                "context_yaml_not_found",
                extra={
                    "component": "context_cache",
                    "action": "load_disk",
                    "result": "not_found",
                    "path": str(path),
                },
            )
            return {}

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logger.warning(
                "context_yaml_invalid_type",
                extra={
                    "component": "context_cache",
                    "action": "load_disk",
                    "result": "invalid_type",
                    "path": str(path),
                    "type": type(data).__name__,
                },
            )
            return {}

        return data

    except yaml.YAMLError as exc:
        logger.warning(
            "context_yaml_parse_error",
            extra={
                "component": "context_cache",
                "action": "load_disk",
                "result": "parse_error",
                "path": str(path),
                "error_type": type(exc).__name__,
            },
        )
        return {}
    except Exception as exc:
        logger.warning(
            "context_yaml_load_error",
            extra={
                "component": "context_cache",
                "action": "load_disk",
                "result": "error",
                "path": str(path),
                "error_type": type(exc).__name__,
            },
        )
        return {}
