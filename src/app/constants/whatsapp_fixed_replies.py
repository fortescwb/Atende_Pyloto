"""Respostas fixas para Quebra-gelos e comandos do WhatsApp.

Conteúdo configurado conforme README.md (Meta "Quebra-gelos" e comandos "/").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class FixedReplyConfig:
    """Configuração de uma resposta fixa.

    Atributos:
        key: Identificador interno da resposta.
        trigger: Texto disparador (exato no painel Meta).
        response_text: Resposta fixa a ser enviada ao usuário.
        prompt_vertical: Vertente sugerida para contexto futuro (opcional).
        kind: Tipo do disparo (quick_reply ou command).
    """

    key: str
    trigger: str
    response_text: str
    prompt_vertical: str | None
    kind: Literal["quick_reply", "command"]


FIXED_REPLIES: tuple[FixedReplyConfig, ...] = (
    FixedReplyConfig(
        key="quebra_gelo_gestao_trafego",
        trigger="Como funciona a Gestão de perfis e Tráfego?",
        response_text=(
            "Gestão de Perfis + Tráfego: presença digital + tráfego pago com foco "
            "em leads e vendas. Inclui estratégia, campanhas e otimização contínua."
        ),
        prompt_vertical="gestao_perfis_trafego",
        kind="quick_reply",
    ),
    FixedReplyConfig(
        key="quebra_gelo_automacao",
        trigger="Como funciona a Automação?",
        response_text=(
            "Automação de atendimento com ou sem IA. Entregamos um painel de gestão "
            "onde é possível assumir conversas atendidas pelo bot/IA e visualizar "
            "os atendimentos em andamento."
        ),
        prompt_vertical="automacao_atendimento",
        kind="quick_reply",
    ),
    FixedReplyConfig(
        key="quebra_gelo_sob_medida",
        trigger="Como funciona o desenvolvimento de Sistemas Sob Medida?",
        response_text=(
            "Sistemas sob medida: realizamos estudo do fluxo atual, ferramentas usadas "
            "e integrações necessárias. Entregamos uma plataforma web ou local "
            "pensada para suas necessidades."
        ),
        prompt_vertical="sob_medida",
        kind="quick_reply",
    ),
    FixedReplyConfig(
        key="quebra_gelo_saas",
        trigger="O que é o SaaS da Pyloto?",
        response_text=(
            "O Pyloto da sua comunicação. SaaS pensado para atender a maior parte "
            "dos nichos e empresas de forma adaptável."
        ),
        prompt_vertical="saas",
        kind="quick_reply",
    ),
    FixedReplyConfig(
        key="cmd_automacao",
        trigger="/automacao",
        response_text=(
            "Automação de atendimento com ou sem IA. Entregamos um painel de gestão "
            "onde é possível assumir conversas atendidas pelo bot/IA e visualizar "
            "os atendimentos em andamento."
        ),
        prompt_vertical="automacao_atendimento",
        kind="command",
    ),
    FixedReplyConfig(
        key="cmd_sob_medida",
        trigger="/sobmedida",
        response_text=(
            "Sistemas sob medida: realizamos estudo do fluxo atual, ferramentas usadas "
            "e integrações necessárias. Entregamos uma plataforma web ou local "
            "pensada para suas necessidades."
        ),
        prompt_vertical="sob_medida",
        kind="command",
    ),
    FixedReplyConfig(
        key="cmd_entregas_servicos",
        trigger="/entregas_servicos",
        response_text=(
            "Pyloto Serviços é o carro-chefe. Fazemos a intermediação operacional entre "
            "prestadores cadastrados e solicitantes (PF ou PJ). Solicitações devem ser "
            "feitas pelo WhatsApp +554291619261."
        ),
        prompt_vertical="intermediacao_entregas",
        kind="command",
    ),
    FixedReplyConfig(
        key="cmd_saas",
        trigger="/saas",
        response_text=(
            "O Pyloto da sua comunicação. SaaS pensado para atender a maior parte "
            "dos nichos e empresas de forma adaptável."
        ),
        prompt_vertical="saas",
        kind="command",
    ),
)
