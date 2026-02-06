"""Loader para contexto de verticais (contextos dinâmicos).

Carrega YAMLs em `src/ai/contexts/vertentes/` com cache,
sem uso de rede, conforme REGRAS_E_PADROES.md.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ai.config.institutional_loader import load_institutional_context

logger = logging.getLogger(__name__)

_VERTICAL_CONTEXT_DIR = Path(__file__).resolve().parents[1] / "contexts" / "vertentes"


class VerticalContextError(Exception):
    """Erro ao carregar contexto vertical."""


@lru_cache(maxsize=1)
def _load_vertical_index() -> dict[str, Path]:
    """Carrega mapeamento de IDs -> arquivo a partir do contexto institucional."""
    context = load_institutional_context()
    services = context.get("servicos_resumo") or context.get("vertentes") or []
    mapping: dict[str, Path] = {}
    for item in services:
        if not isinstance(item, dict):
            continue
        service_id = (item.get("id") or "").strip()
        filename = (item.get("context_file") or "").strip()
        if not service_id:
            continue
        if filename:
            mapping[service_id] = _VERTICAL_CONTEXT_DIR / filename
    return mapping


@lru_cache(maxsize=32)
def load_vertical_context(vertical_id: str) -> dict[str, Any] | None:
    """Carrega contexto vertical (YAML) pelo ID.

    Args:
        vertical_id: ID da vertical (ex: "saas", "sob_medida").

    Returns:
        Dict do YAML ou None se nao encontrado/invalidado.
    """
    if not vertical_id:
        return None

    vertical_id = vertical_id.strip()
    index = _load_vertical_index()
    path = index.get(vertical_id)
    if path is None:
        candidate = _VERTICAL_CONTEXT_DIR / f"{vertical_id}.yaml"
        candidate_core = _VERTICAL_CONTEXT_DIR / vertical_id / "core.yaml"
        if candidate.exists():
            path = candidate
        elif candidate_core.exists():
            path = candidate_core
        else:
            logger.info(
                "vertical_context_not_found",
                extra={"vertical_id": vertical_id},
            )
            return None

    if not path.exists():
        logger.warning(
            "vertical_context_file_missing",
            extra={"vertical_id": vertical_id, "path": str(path)},
        )
        return None

    try:
        with path.open("r", encoding="utf-8") as f:
            context = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        logger.error(
            "vertical_context_yaml_error",
            extra={"vertical_id": vertical_id, "error": str(exc)},
        )
        return None

    if not isinstance(context, dict):
        logger.warning(
            "vertical_context_invalid_format",
            extra={"vertical_id": vertical_id, "path": str(path)},
        )
        return None

    return context


def clear_vertical_cache() -> None:
    """Limpa cache dos contextos verticais (util em testes)."""
    _load_vertical_index.cache_clear()
    load_vertical_context.cache_clear()
