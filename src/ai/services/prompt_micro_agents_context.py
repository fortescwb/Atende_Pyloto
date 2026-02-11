"""Helpers de contexto e assets dos micro agentes.

P2-1: Integrado cache inteligente para reduzir I/O de YAMLs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai.utils.context_cache import load_yaml_cached

_VERTENTES_DIR = Path(__file__).resolve().parents[1] / "contexts" / "vertentes"


def cases_index_path(folder: str) -> Path:
    """Retorna caminho do índice de casos da vertical."""
    return _VERTENTES_DIR / folder / "cases" / "index.yaml"


def context_path(folder: str, relative: str) -> str:
    """Monta caminho relativo aceito pelo loader de templates."""
    return f"vertentes/{folder}/{relative}"


def context_exists(relative_path: str) -> bool:
    """Verifica se contexto relativo existe em diretório permitido."""
    try:
        rel = Path(relative_path)
        if rel.is_absolute() or ".." in rel.parts:
            return False
        path = (_VERTENTES_DIR / rel.relative_to("vertentes")).resolve()
    except Exception:
        return False
    return path.exists()


def load_yaml(path: Path) -> dict[str, Any]:
    """Lê YAML e retorna dict seguro.

    P2-1: Usa cache com TTL 5min para reduzir I/O repetido.
    """
    return load_yaml_cached(path, ttl_seconds=300)
