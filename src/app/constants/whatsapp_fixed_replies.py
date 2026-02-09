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
            "Utilizamos um software próprio para gestão de perfis e tráfego, com "
            "relatórios detalhados e insights para maximizar resultados."
        ),
        prompt_vertical="gestao_perfis_trafego",
        kind="quick_reply",
    ),
    FixedReplyConfig(
        key="quebra_gelo_automacao",
        trigger="Como funciona a Automação?",
        response_text=(
            "Automação de atendimento com ou sem IA. Entregamos um painel de gestão "
            "onde é possível visualizar os atendimentos em andamento e assumir as "
            "conversas atendidas pelo bot/IA. Separamos em dois tipos de automação: "
            "1) Automação simples: respostas pré-definidas para perguntas frequentes, "
            "sem IA. "
            "2) Automação com IA: utiliza inteligência artificial para responder a perguntas "
            "mais complexas e personalizadas, aprendendo com as interações para "
            "melhorar continuamente."
        ),
        prompt_vertical="automacao_atendimento",
        kind="quick_reply",
    ),
    FixedReplyConfig(
        key="quebra_gelo_sob_medida",
        trigger="Como funciona o desenvolvimento de Sistemas Sob Medida?",
        response_text=(
            "A equipe Pyloto faz um estudo detalhado sobre o processo atual da sua empresa, "
            "quais ferramentas utilizam, quais sistemas podem/devem ser integrados, etc. "
            "Após isso, desenhamos "
            "um sistema exclusivo, pensado detalhadamente para a necessidade da sua empresa."
        ),
        prompt_vertical="sob_medida",
        kind="quick_reply",
    ),
    FixedReplyConfig(
        key="quebra_gelo_saas",
        trigger="O que é o SaaS da Pyloto?",
        response_text=(
            "O Pyloto da sua comunicação. O SaaS da Pyloto, pensado para atender a maior parte "
            "dos nichos e empresas de maneira adaptável, esta atualmente em desenvolvimento. Em "
            "breve será lançado "
            "para bater de frente com gigantes do mercado de CRM."
        ),
        prompt_vertical="saas",
        kind="quick_reply",
    ),
    FixedReplyConfig(
        key="cmd_automacao",
        trigger="/automacao",
        response_text=(
            "Na automação de atendimento, nós entregamos um painel com inbox centralizada "
            "dos canais que serão automatizados, onde você poderá acompanhar o atendimento "
            "do Bot/IA e assumir as conversas "
            "com potencial de conversão."
        ),
        prompt_vertical="automacao_atendimento",
        kind="command",
    ),
    FixedReplyConfig(
        key="cmd_sob_medida",
        trigger="/sobmedida",
        response_text=(
            "A equipe Pyloto faz um estudo detalhado sobre o processo atual da sua empresa, "
            "quais ferramentas utilizam, quais sistemas podem/devem ser integrados, etc. "
            "Após isso, desenhamos um sistema exclusivo, "
            "pensado detalhadamente para a necessidade da sua empresa."
        ),
        prompt_vertical="sob_medida",
        kind="command",
    ),
    FixedReplyConfig(
        key="cmd_entregas_servicos",
        trigger="/entregas_servicos",
        response_text=(
            "Pyloto Serviços é o nosso carro-chefe. Fazemos a intermediação operacional entre "
            "prestadores cadastrados e solicitantes (PF ou PJ). As solicitações devem ser "
            "feitas pelo WhatsApp +554291619261."
        ),
        prompt_vertical="intermediacao_entregas",
        kind="command",
    ),
    FixedReplyConfig(
        key="cmd_saas",
        trigger="/saas",
        response_text=(
            "O Pyloto da sua comunicação. O SaaS da Pyloto, pensado para atender a maior parte "
            "dos nichos e empresas de maneira adaptável, esta atualmente em desenvolvimento. Em "
            "breve será lançado para bater de frente com gigantes do mercado de CRM."
        ),
        prompt_vertical="saas",
        kind="command",
    ),
)
