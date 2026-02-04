"""Loader de configuração YAML para agentes.

Carrega e valida configurações de config/agents/{agent_name}.yaml.
Conforme REGRAS_E_PADROES.md § 2.1: ai/config contém configuração global.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Diretório base de configuração de agentes (src/config/agents/)
_CONFIG_DIR = Path(__file__).parent.parent.parent / "config" / "agents"


@dataclass(frozen=True, slots=True)
class AgentConfig:
    """Configuração de um agente LLM."""

    agent_name: str
    version: str
    description: str
    model_name: str
    temperature: float
    max_tokens: int
    timeout_seconds: int
    behavior: dict[str, Any]


@functools.lru_cache(maxsize=8)
def load_agent_config(agent_name: str) -> AgentConfig:
    """Carrega configuração do agente de YAML (com cache).

    Args:
        agent_name: Nome do agente (ex: "state_agent", "response_agent")

    Returns:
        AgentConfig com dados do YAML

    Raises:
        FileNotFoundError: Se arquivo YAML não existe
        ValueError: Se YAML tem schema inválido
    """
    yaml_path = _CONFIG_DIR / f"{agent_name}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Config não encontrada: {yaml_path}")

    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return _parse_config(data, agent_name)


def _parse_config(data: dict[str, Any], agent_name: str) -> AgentConfig:
    """Valida e parseia dados do YAML."""
    if not isinstance(data, dict):
        raise ValueError(f"Config de {agent_name} deve ser dict")

    model = data.get("model", {})
    behavior = data.get("behavior", {})

    return AgentConfig(
        agent_name=str(data.get("agent_name", agent_name)),
        version=str(data.get("version", "1.0.0")),
        description=str(data.get("description", "")),
        model_name=str(model.get("name", "gpt-4o-mini")),
        temperature=float(model.get("temperature", 0.3)),
        # Support both new 'max_completion_tokens' and legacy 'max_tokens' keys in YAML
        max_tokens=int(model.get("max_completion_tokens", model.get("max_tokens", 500))),
        timeout_seconds=int(model.get("timeout_seconds", 10)),
        behavior=behavior if isinstance(behavior, dict) else {},
    )


def get_all_agent_configs() -> dict[str, AgentConfig]:
    """Carrega configurações de todos os agentes."""
    agents = ["state_agent", "response_agent", "message_type_agent", "decision_agent"]
    return {name: load_agent_config(name) for name in agents}
