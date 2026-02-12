"""Loaders de assets YAML de prompt/contexto.

Centraliza leitura de arquivos YAML usados na montagem de prompts, com cache.

Observação: IO local (filesystem) é permitido aqui por se tratar de configuração
e assets versionados do repositório (sem rede).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_AI_DIR = Path(__file__).resolve().parents[1]
_CONTEXTS_DIR = _AI_DIR / "contexts"
_PROMPTS_YAML_DIR = _AI_DIR / "prompts" / "yaml"


class PromptAssetError(RuntimeError):
    """Erro ao carregar assets YAML de prompt/contexto."""


def _resolve_relative_path(base_dir: Path, relative_path: str) -> Path:
    if not relative_path:
        raise PromptAssetError("relative_path vazio")
    rel = Path(relative_path)
    # Em Windows, caminhos iniciando com "/" podem nao ser reconhecidos por
    # Path.is_absolute(); por isso validamos tambem por prefixo.
    if rel.is_absolute() or relative_path.startswith(("/", "\\")):
        raise PromptAssetError("relative_path deve ser relativo")
    if ".." in rel.parts:
        raise PromptAssetError("relative_path invalido (..) não permitido")
    return (base_dir / rel).resolve()


@lru_cache(maxsize=256)
def load_context_text(relative_path: str) -> str:
    """Carrega texto bruto de um YAML em `src/ai/contexts/`."""
    path = _resolve_relative_path(_CONTEXTS_DIR, relative_path)
    if not path.exists():
        raise PromptAssetError(f"Arquivo de contexto nao encontrado: {relative_path}")
    if not path.is_file():
        raise PromptAssetError(f"Caminho de contexto invalido: {relative_path}")
    return path.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=256)
def load_context_for_prompt(relative_path: str) -> str:
    """Carrega um contexto pronto para prompt.

    Regra:
      - Se YAML tiver `prompt_injection` (str), usa ele.
      - Senão, se tiver `prompt_summary` (str), usa ele.
      - Caso contrário, usa o texto bruto do arquivo (YAML completo).
    """
    raw = load_context_text(relative_path)
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:  # pragma: no cover
        raise PromptAssetError(f"YAML invalido em {relative_path}: {exc}") from exc

    if isinstance(data, dict):
        for key in ("prompt_injection", "prompt_summary"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return raw


@lru_cache(maxsize=256)
def load_prompt_yaml(relative_path: str) -> dict[str, Any]:
    """Carrega YAML em `src/ai/prompts/yaml/` como dict."""
    path = _resolve_relative_path(_PROMPTS_YAML_DIR, relative_path)
    if not path.exists():
        raise PromptAssetError(f"Arquivo de prompt YAML nao encontrado: {relative_path}")
    if not path.is_file():
        raise PromptAssetError(f"Caminho de prompt YAML invalido: {relative_path}")

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:  # pragma: no cover
        raise PromptAssetError(f"YAML invalido em {relative_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise PromptAssetError(f"YAML de prompt deve ser dict: {relative_path}")
    return data


def load_prompt_template(relative_path: str) -> str:
    """Carrega campo `template` de um YAML em `src/ai/prompts/yaml/`."""
    data = load_prompt_yaml(relative_path)
    template = data.get("template")
    if not isinstance(template, str) or not template.strip():
        raise PromptAssetError(f"Campo `template` ausente/invalido: {relative_path}")
    return template


def load_system_prompt(relative_path: str) -> str:
    """Carrega campo `system_prompt` de um YAML em `src/ai/prompts/yaml/`."""
    data = load_prompt_yaml(relative_path)
    system_prompt = data.get("system_prompt")
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise PromptAssetError(f"Campo `system_prompt` ausente/invalido: {relative_path}")
    return system_prompt


def clear_prompt_assets_cache() -> None:
    """Limpa caches (útil em testes)."""
    load_context_text.cache_clear()
    load_context_for_prompt.cache_clear()
    load_prompt_yaml.cache_clear()
