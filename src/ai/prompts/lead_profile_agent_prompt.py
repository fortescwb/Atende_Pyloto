"""Prompt do LeadProfileAgent (Agente 2-B) — gpt-5-nano.

Extrai informações relevantes da conversa para salvar no LeadProfile.
Identifica: nome, sobrenome, email, empresa, endereço, necessidades, etc.

REGRA: Apenas extração de dados, sem geração de resposta.
Atualiza informações pessoais de forma inteligente (não sobrescreve, complementa).
"""

from __future__ import annotations

# Prompt minimalista para nano — extração de dados
LEAD_PROFILE_AGENT_SYSTEM = """Extraia informações do usuário para o LeadProfile.

## CAMPOS PESSOAIS
- name: Nome (primeiro nome)
- surname: Sobrenome
- email: Email
- company: Empresa
- city: Cidade
- state: Estado (sigla)

## INFORMAÇÕES PESSOAIS (texto livre)
Campo "personal_info" para anotar informações relevantes:
- Situação familiar (casado, filhos, etc)
- Profissão
- Preferências
- Qualquer informação útil para relacionamento da Pyloto com o lead

REGRA: Atualizar personal_info de forma inteligente.
Se já existe "Tem 3 filhos" e nova info diz "filhos moram com a mãe",
retornar: "Tem 3 filhos que moram com a mãe"

## NECESSIDADES (máximo 3 ativas)
- need_type: saas, custom_system, website, landing_page, traffic_management, automation, other
- title: Resumo curto
- details: Detalhes específicos
- urgency: alta/média/baixa

REGRAS:
- Só preencha campos EXPLICITAMENTE mencionados
- Não invente informações
- O telefone já está no perfil (não extrair)
- Retorne apenas novos dados ou atualizações

Responda JSON:
{
    "personal": {"campo": "valor", ...},
    "personal_info_update": "<texto atualizado ou null>",
    "need": {"need_type": "...", "title": "...", "details": "...", "urgency": "..."} ou null,
    "confidence": <0.0-1.0>
}

Se nenhuma informação nova: {"personal": {}, "personal_info_update": null, "need": null, "confidence": 1.0}
"""

LEAD_PROFILE_AGENT_USER_TEMPLATE = """## Perfil atual
{current_profile}

## Informações pessoais atuais
{current_personal_info}

## Necessidades ativas
{current_needs}

## Mensagem do usuário
{user_input}

Extraia novas informações. JSON apenas."""


def format_lead_profile_agent_prompt(
    user_input: str,
    current_profile: str = "",
    current_personal_info: str = "",
    current_needs: str = "",
) -> str:
    """Formata prompt para o LeadProfileAgent.

    Args:
        user_input: Mensagem do usuário
        current_profile: Perfil atual formatado
        current_personal_info: Texto de informações pessoais atual
        current_needs: Necessidades ativas formatadas
    """
    return LEAD_PROFILE_AGENT_USER_TEMPLATE.format(
        user_input=user_input[:500],
        current_profile=current_profile[:300] if current_profile else "Novo contato",
        current_personal_info=current_personal_info[:200] if current_personal_info else "(vazio)",
        current_needs=current_needs[:300] if current_needs else "Nenhuma",
    )
