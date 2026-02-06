"""Builders para contextos de prompt (SYSTEM/USER).

Padronização:
  - Assets de contexto ficam em `src/ai/contexts/**.yaml`
  - SYSTEM: `core/system_role.yaml`, `core/mindset.yaml`, `core/vertentes_basico.yaml`,
    `regras/json_output.yaml`
  - USER: `core/sobre_pyloto.yaml` + (opcional) `vertentes/<intent>.yaml`
"""

from __future__ import annotations

from ai.config.prompt_assets_loader import load_context_for_prompt

_ALWAYS_SYSTEM = (
    "core/system_role.yaml",
    "core/mindset.yaml",
    "core/vertentes_basico.yaml",
    "regras/json_output.yaml",
)

_ALWAYS_USER = ("core/sobre_pyloto.yaml",)

_INTENT_FILE_ALIASES: dict[str, str] = {
    # curtos (detect_intent)
    "automacao": "automacao",
    "entregas": "entregas",
    "trafego": "trafego",
    # canônicos (ContactCard.primary_interest)
    "automacao_atendimento": "automacao",
    "intermediacao_entregas": "entregas",
    "gestao_perfis_trafego": "trafego",
    # outros IDs existentes no repo
    "sistema_sob_medida": "sob_medida",
    "sob_medida": "sob_medida",
    "saas": "saas",
}


def build_contexts(tenant_intent: str | None = None) -> dict[str, str]:
    """Carrega e junta contextos padronizados.

    Args:
        tenant_intent: ID curto/canônico da vertente (opcional).
    """
    system_parts = [load_context_for_prompt(path) for path in _ALWAYS_SYSTEM]
    system_context = "\n\n".join(part for part in system_parts if part).strip()

    institutional_parts = [load_context_for_prompt(path) for path in _ALWAYS_USER]
    institutional_context = "\n\n".join(part for part in institutional_parts if part).strip()

    tenant_context = ""
    if tenant_intent:
        key = tenant_intent.strip().lower()
        filename = _INTENT_FILE_ALIASES.get(key)
        if filename:
            tenant_context = load_context_for_prompt(f"vertentes/{filename}.yaml").strip()

    user_parts = [institutional_context]
    if tenant_context:
        user_parts.append(tenant_context)
    user_context = "\n\n".join(part for part in user_parts if part).strip()

    return {
        "system_context": system_context,
        "institutional_context": institutional_context,
        "tenant_context": tenant_context,
        "user_context": user_context,
    }
