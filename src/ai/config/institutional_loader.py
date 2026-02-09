"""Loader para contexto institucional.

Carrega e disponibiliza informações institucionais do YAML
para uso nos prompts dos agentes LLM.

Conforme REGRAS_E_PADROES.md § 2.1: ai/config contém configuração de IA.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Path do arquivo de contexto institucional (padronizado em YAML)
_INSTITUTIONAL_CONTEXT_PATH = (
    Path(__file__).resolve().parents[1] / "contexts" / "core" / "sobre_pyloto.yaml"
)


class InstitutionalContextError(Exception):
    """Erro ao carregar contexto institucional."""


@lru_cache(maxsize=1)
def load_institutional_context() -> dict[str, Any]:
    """Carrega contexto institucional do YAML (cached).

    Returns:
        Dict com dados institucionais

    Raises:
        InstitutionalContextError: Se arquivo não existir ou YAML inválido
    """
    if not _INSTITUTIONAL_CONTEXT_PATH.exists():
        logger.warning(
            "Arquivo de contexto institucional não encontrado",
            extra={"path": str(_INSTITUTIONAL_CONTEXT_PATH)},
        )
        return _get_fallback_context()

    try:
        with _INSTITUTIONAL_CONTEXT_PATH.open("r", encoding="utf-8") as f:
            context = yaml.safe_load(f)
            if not isinstance(context, dict):
                raise InstitutionalContextError("YAML deve ser um dicionário")
            # Compat: manter chaves legadas esperadas pelos testes/consumidores.
            if "vertentes" not in context and "servicos" in context:
                context["vertentes"] = context["servicos"]
            if "vertentes" not in context and "servicos_resumo" in context:
                context["vertentes"] = context["servicos_resumo"]
            if "horario_atendimento_presencial" not in context:
                presencial = context.get("endereco", {}).get("atendimento_presencial")
                if presencial:
                    context["horario_atendimento_presencial"] = presencial
            if "horario_atendimento" not in context and "horario_atendimento_presencial" in context:
                context["horario_atendimento"] = context["horario_atendimento_presencial"]
            logger.debug("Contexto institucional carregado com sucesso")
            return context
    except yaml.YAMLError as e:
        logger.error(
            "Erro ao parsear YAML institucional",
            extra={"error": str(e)},
        )
        return _get_fallback_context()


def _get_fallback_context() -> dict[str, Any]:
    """Retorna contexto mínimo de fallback."""
    return {
        "empresa": {
            "nome": "Pyloto",
            "descricao": "Empresa de tecnologia e serviços",
        },
        "contato": {
            "email": "contato@pyloto.com.br",
        },
        "vertentes": [],
    }


def get_institutional_prompt_section() -> str:
    """Retorna seção formatada para inserir em prompts.

    Formata as informações institucionais de forma legível
    para inclusão nos prompts dos agentes LLM.
    """
    context = load_institutional_context()
    sections = [
        _format_empresa_section(context.get("empresa", {})),
        _format_contato_section(context.get("contato", {})),
        _format_endereco_section(context.get("endereco", {})),
        _format_horario_section(context.get("horario_atendimento", {})),
        _format_servicos_section(context.get("vertentes", [])),
    ]
    return "\n\n".join(section for section in sections if section)


def get_service_info(service_id: str) -> dict[str, Any] | None:
    """Retorna informações de um serviço específico.

    Args:
        service_id: ID do serviço (ex: 'saas', 'entregas')

    Returns:
        Dict com informações do serviço ou None se não encontrado
    """
    context = load_institutional_context()
    vertentes = context.get("vertentes", [])

    for v in vertentes:
        if v.get("id") == service_id:
            return v
    return None


def get_contact_info() -> dict[str, str]:
    """Retorna informações de contato.

    Returns:
        Dict com telefone, email, site, etc.
    """
    context = load_institutional_context()
    return context.get("contato", {})


def get_address_info() -> dict[str, str]:
    """Retorna informações de endereço.

    Returns:
        Dict com rua, numero, cidade, etc.
    """
    context = load_institutional_context()
    return context.get("endereco", {})


def get_business_hours() -> dict[str, Any]:
    """Retorna horário de atendimento.

    Returns:
        Dict com horários por dia da semana
    """
    context = load_institutional_context()
    return context.get("horario_atendimento", {})


def clear_cache() -> None:
    """Limpa cache do contexto institucional.

    Útil para testes ou quando o arquivo YAML for atualizado.
    """
    load_institutional_context.cache_clear()


def _format_empresa_section(empresa: dict[str, Any]) -> str:
    if not empresa:
        return ""
    lines = [f"**Empresa:** {empresa.get('nome', 'Pyloto')}"]
    if desc := empresa.get("descricao"):
        lines.append(f"  {desc}")
    return "\n".join(lines)


def _format_contato_section(contato: dict[str, Any]) -> str:
    if not contato:
        return ""
    lines = ["**Contato:**"]
    if tel := contato.get("telefone"):
        lines.append(f"  - Telefone: {tel}")
    if email := contato.get("email"):
        lines.append(f"  - Email: {email}")
    if site := contato.get("site"):
        lines.append(f"  - Site: {site}")
    return "\n".join(lines)


def _format_endereco_section(endereco: dict[str, Any]) -> str:
    if not (endereco and endereco.get("rua")):
        return ""
    end_str = (
        f"{endereco.get('rua', '')}, {endereco.get('numero', '')}"
        f" - {endereco.get('bairro', '')}, {endereco.get('cidade', '')}"
        f"/{endereco.get('estado', '')}"
    )
    return f"**Endereço:** {end_str}"


def _format_horario_section(horario: dict[str, Any]) -> str:
    if not horario:
        return ""
    dias_uteis = horario.get("dias_uteis", {})
    if not dias_uteis:
        return ""
    return (
        f"**Horário:** Seg-Sex {dias_uteis.get('inicio', '08:00')}-"
        f"{dias_uteis.get('fim', '18:00')}"
    )


def _format_servicos_section(vertentes: list[dict[str, Any]]) -> str:
    if not vertentes:
        return ""
    lines = ["**Serviços:**"]
    for vertente in vertentes:
        lines.append(f"  - {vertente.get('nome', '')}: {vertente.get('descricao', '')}")
    return "\n".join(lines)
