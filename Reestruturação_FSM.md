# Proposta: FSM v2 com Estados Compostos + Supervisor LLM

**Autor:** Arquitetura Técnica Pyloto  
**Data:** 12 de fevereiro de 2026  
**Versão:** 2.0 - Revisão Crítica  
**Status:** Aprovação Pendente

---

## 1. Problema Identificado

### 1.1 Sintomas em Produção

- Conversas repetem perguntas já respondidas (~35% de redundância)
- Sistema não rastreia informações coletadas estruturadamente
- Estados terminais (`SCHEDULED_FOLLOWUP`, `CLOSED`) impedem retorno contextualizado
- Leads "mortos" que retornam (15-20% dentro de 30 dias) iniciam conversa do zero
- Não há distinção entre "usuário desistiu" vs "usuário abusivo" vs "concluiu com sucesso"

### 1.2 Causa Raiz Estrutural

**Dessincronia arquitetural crítica:**

A FSM atual opera com estados puramente técnicos (`TRIAGE`, `COLLECTING_INFO`, `GENERATING_RESPONSE`) enquanto o sistema de contextos dinâmicos (`dynamic_context_loader.py`) carrega conhecimento semântico de negócio (`vertentes/saas/`, `vertentes/automacao/`).

**Resultado:** A LLM sabe que o usuário está interessado em SaaS e já forneceu email + empresa, mas a FSM continua em `COLLECTING_INFO` genérico sem memória estruturada do que foi coletado.

### 1.3 Limitação Arquitetural

**Estado atual - insuficiente:**
- `SessionState.COLLECTING_INFO` → Coletando o quê? Para qual produto? Com qual objetivo?

**Contexto existe, mas desacoplado:**
- `loaded_contexts = ["vertentes/saas/core.yaml", "vertentes/saas/pricing.yaml"]`
- Sistema carrega conhecimento, mas FSM não acompanha evolução semântica

**Consequência:** A FSM é um semáforo técnico sem consciência de negócio.

---

## 2. Solução Proposta: FSM Híbrida com Supervisor LLM

### 2.1 Conceito Central

Transformar a FSM de **mecanismo técnico de controle de fluxo** em **sistema contextualmente consciente** através de três pilares:

**Pilar 1: Estados Compostos**

```
Estado Real = (FlowState × Set<BusinessContext> × CollectedFields)
```

**Pilar 2: Supervisor LLM**
- LLM especializada que decide transições de estado
- Valida coerência entre contexto de negócio e estado técnico
- Detecta abuso e comportamento anômalo
- Projeta custo até conversão

**Pilar 3: Prompts Compostos**
- Sistema de herança/composição de templates
- 15 blocos reutilizáveis vs 36+ arquivos monolíticos
- Reduz inconsistência e facilita evolução

### 2.2 Vantagens Operacionais

| Dimensão | Antes | Depois |
|----------|-------|--------|
| **Escalabilidade** | Adicionar produto = reescrever estados | Adicionar contexto isolado |
| **Rastreabilidade** | Histórico de mensagens não-estruturado | `collected_fields` explícitos + auditoria |
| **Manutenibilidade** | Alterar SaaS afeta todo sistema | Contextos isolados |
| **Retorno de leads** | Impossível retomar contexto | Estado recuperável com histórico |
| **Controle de custo** | Sem visibilidade | Tracking + projeção por sessão |
| **Defesa contra abuso** | Inexistente | Métricas + circuit breaker |

---

## 3. Arquitetura Detalhada

### 3.1 FlowState - Estados de Pipeline

**Princípio:** Estados representam **onde** a conversa está no funil, não **sobre o quê** está falando.

#### Estados Ativos (não-terminais)

- **INITIAL** - Primeira interação, identificação básica
- **QUALIFYING** - Qualificando necessidade/fit/urgência
- **DEEP_DIVE** - Aprofundamento em produto/serviço específico
- **SCHEDULING** - Processo ativo de agendamento (coletando data/hora/preferências)
- **AWAITING_RETURN** - Aguardando retorno agendado ou follow-up programado

#### Estados de Espera Controlada

- **AWAITING_RETURN** - Não é terminal, pode retornar a `DEEP_DIVE` se usuário voltar antes do agendado

#### Estados Terminais com Janela de Reabertura

**Crítico:** Estados terminais **não são permanentes**. Possuem janelas de reabertura baseadas em tipo de encerramento.

- **CLOSED_SUCCESS** - Lead convertido ou agendamento confirmado
  - Janela de reabertura: 7 dias (reagendamento, dúvidas pós-venda)
  
- **CLOSED_UNQUALIFIED** - Lead não-qualificado (sem budget, timing errado, fora do ICP)
  - Janela de reabertura: 30 dias (situação pode mudar)
  
- **CLOSED_NO_RESPONSE** - Timeout por inatividade
  - Janela de reabertura: 14 dias
  
- **CLOSED_ABUSE** - Comportamento abusivo detectado
  - Sem reabertura automática, requer aprovação humana

- **HANDOFF_HUMAN** - Escalado para atendimento humano
  - Não reabre automaticamente (humano assume controle)

**Lógica de reabertura:**
- Se usuário retorna dentro da janela: sistema restaura contexto + `collected_fields`
- Se retorna após janela: inicia novo ciclo mas mantém histórico acessível
- Reabertura sempre registrada em `transition_history` para auditoria

### 3.2 BusinessContext - Contextos de Negócio

**Mudança crítica:** Não é enum singular, é **set de contextos ativos**.

**Justificativa:** Usuário pode ter interesse híbrido ("Quero SaaS para delivery + automação de marketing"). Forçar escolha única perde informação.

#### Contextos Disponíveis

- **UNKNOWN** - Ainda não identificado (estado inicial)
- **SAAS** - Plataforma SaaS Pyloto
- **AUTOMACAO** - Automação customizada
- **ENTREGAS** - Gestão de entregas
- **TRAFEGO** - Gestão de tráfego pago
- **SOB_MEDIDA** - Desenvolvimento sob medida

#### Estrutura na Sessão

```
active_contexts: set[BusinessContext]  # Todos os contextos identificados
primary_intent: BusinessContext | None  # Definido pelo Supervisor LLM quando confiança > 0.85
```

**Exemplo real:**
```
active_contexts = {SAAS, AUTOMACAO}
primary_intent = SAAS  # LLM decidiu que foco principal é SaaS, automação é secundário
```

### 3.3 CollectedFields - Memória Estruturada

**Princípio:** Substituir histórico de mensagens não-estruturado por campos validados e categorizados.

#### Categorias de Campos

**Identificação Básica:**
- `nome`, `email`, `telefone`, `empresa`

**Qualificação:**
- `cargo`, `tamanho_empresa`, `segmento`, `dor_principal`

**Contexto de Decisão:**
- `budget_range`, `urgencia`, `decisor`, `processo_compra`

**Interesse Específico:**
- `features_interesse`, `integracao_necessaria`, `volume_operacao`

**Temporal/Agendamento:**
- `disponibilidade`, `preferencia_contato`, `melhor_horario`

**Validação e Qualidade:**
- Cada campo tem `source` (qual mensagem originou)
- Cada campo tem `confidence` (0.0-1.0, definido pelo Supervisor)
- Campos podem ser `validated=True/False` (ex: email teve syntax check)

**Anti-padrão bloqueado:**
```
# ERRADO - permitiria isso
collected_fields = {
    "resposta_1": "quero saas",
    "resposta_2": "teste@teste.com",
    "resposta_3": "aaa"
}

# CERTO - estruturado e validável
collected_fields = {
    "interesse_primario": {
        "value": "saas", 
        "confidence": 0.95,
        "source": "message_3",
        "validated": True
    },
    "email": {
        "value": "teste@teste.com",
        "confidence": 0.60,  # baixa confiança = email suspeito
        "source": "message_5",
        "validated": False  # falhou syntax check
    }
}
```

### 3.4 Supervisor LLM - Cérebro Decisório

**Papel:** Orquestrador mestre que decide transições, valida coerência e projeta riscos.

#### Responsabilidades

**1. Decisão de Transição de Estado**
- Recebe: estado atual + contexto + mensagem do usuário + campos coletados
- Retorna: próximo estado sugerido + confiança + raciocínio explícito

**2. Validação de Coerência**
- Verifica se resposta gerada pela LLM de conteúdo está alinhada com:
  - Estado atual
  - Contexto de negócio
  - Campos já coletados (não repetir perguntas)
  - Tom da marca

**3. Detecção de Abuso**
- Identifica padrões suspeitos:
  - Respostas repetitivas ("teste", "aaa", "123")
  - Transições muito rápidas (> 5 estados em < 2 min)
  - Campos inválidos consecutivos
  - Consumo anômalo de tokens

**4. Projeção de Custo**
- Estima custo até conversão baseado em:
  - Estado atual + campos faltantes
  - Histórico de conversões similares
  - Complexidade do contexto
- Sugere downgrade de modelo se projeção > threshold

**5. Extração e Validação de Campos**
- Extrai campos estruturados da mensagem do usuário
- Valida sintaxe (email, telefone)
- Calcula confidence score
- Identifica campos conflitantes com dados anteriores

#### Arquitetura Interna do Supervisor

**Input:**
- `SessionFSM` completo
- `user_message` (nova mensagem)
- `generated_response` (resposta candidata da LLM de conteúdo)

**Output:**
- `StateEvaluation` (decisão de transição)
- `FieldsExtracted` (novos campos identificados)
- `CoherenceCheck` (validação da resposta)
- `AbuseFlags` (indicadores de comportamento suspeito)
- `CostProjection` (estimativa de custo)

**Modelo:** GPT-4 (precisa de raciocínio complexo, não pode ser 3.5)

**Latência:** ~400-600ms (aceitável, não está no caminho crítico de resposta ao usuário)

**Fallback:** Se Supervisor falhar, sistema mantém estado atual e loga erro para revisão humana

---

## 4. Sistema de Prompts Compostos

### 4.1 Problema com Abordagem Naive

**36 templates (6 estados × 6 contextos) vira pesadelo operacional:**

- Em 1 ano: 6 estados × 10 contextos × 3 tons = 180 arquivos
- Inconsistência: atualiza um, esquece outros
- Testing: como validar coerência entre todos?
- Duplicação: 70% do conteúdo é idêntico entre templates

### 4.2 Solução: Hierarquia de Composição

**Estrutura:**

```
prompts/
├── base/
│   ├── tone.yaml              # Tom da Pyloto (sempre incluso)
│   ├── safety.yaml            # Restrições (nunca prometer, não coletar CPF, etc)
│   ├── format.yaml            # Formato de resposta esperado
│   └── field_validation.yaml  # Regras de validação de campos
│
├── flow/
│   ├── QUALIFYING.yaml        # Lógica de qualificação genérica
│   ├── DEEP_DIVE.yaml         # Lógica de aprofundamento
│   ├── SCHEDULING.yaml        # Lógica de agendamento
│   └── AWAITING_RETURN.yaml   # Lógica de retorno
│
└── context/
    ├── SAAS.yaml              # Conhecimento de produto SaaS
    ├── AUTOMACAO.yaml         # Conhecimento de automação
    ├── ENTREGAS.yaml          # Conhecimento de entregas
    └── [...]
```

**Composição em runtime:**

Sistema carrega e mescla blocos necessários:
- Base (sempre)
- Flow (baseado em `flow_state`)
- Context (baseado em `active_contexts`, pode ser múltiplo)
- Fields (injeta `collected_fields` para evitar repetição)

**Resultado:** 15 blocos reutilizáveis em vez de 36+ arquivos monolíticos.

**Benefício adicional:** Permite A/B testing de componentes isolados (ex: testar 2 versões de `tone.yaml` sem replicar 36 arquivos)

### 4.3 Injeção Dinâmica de Campos Coletados

**Crítico:** Prompt sempre inclui seção explícita com campos já coletados.

```
--- INFORMAÇÕES JÁ COLETADAS (NÃO PERGUNTAR NOVAMENTE) ---
Nome: João Silva (confidence: 0.95)
Email: joao@techcorp.com (confidence: 0.88, validado)
Empresa: Tech Corp (confidence: 0.92)
Interesse: SaaS para gestão de entregas (confidence: 0.95)

--- INFORMAÇÕES FALTANTES PARA QUALIFICAÇÃO ---
- Tamanho da operação (entregas/mês)
- Budget disponível
- Urgência da implementação
```

Isso força a LLM a não repetir perguntas e focar no que falta.

---

## 5. Matriz de Transições e Guardas

### 5.1 Filosofia de Guardas

**Princípio:** Guardas validam **regras de negócio hard**, não heurísticas.

**O que pertence a guardas:**
- Validações determinísticas (ex: `tem email AND telefone`)
- Limites de custo/tempo/tentativas
- Restrições de compliance

**O que NÃO pertence a guardas:**
- Detecção de intenção (ex: "usuário quer agendar") → isso é responsabilidade do Supervisor LLM
- Interpretação de sentimento
- Inferência de contexto

### 5.2 Transições Principais

**INITIAL → QUALIFYING**
- Guarda: `business_context == UNKNOWN`
- Objetivo: Identificar área de interesse

**QUALIFYING → DEEP_DIVE**
- Guarda: `primary_intent != None AND confidence > 0.7`
- Supervisor decide quando qualificação está completa

**DEEP_DIVE → SCHEDULING**
- Guardas obrigatórias:
  - `has_minimum_fields(['nome', 'contato'])`
  - `scheduling_intent_confidence > 0.8` (vem do Supervisor)
  - `abuse_metrics.is_clean()`

**DEEP_DIVE → CLOSED_SUCCESS**
- Guardas:
  - `self_serve_completed == True` (usuário conseguiu o que queria sem agendamento)
  - `explicit_no_need_human` (usuário disse que não precisa mais de ajuda)

**DEEP_DIVE → CLOSED_UNQUALIFIED**
- Guardas:
  - `disqualification_reason IN ['fora_do_budget', 'timing_errado', 'fora_icp']`
  - `supervisor_confidence > 0.85` (alta confiança na desqualificação)

**SCHEDULING → AWAITING_RETURN**
- Guarda: `scheduled_followup != None`

**AWAITING_RETURN → DEEP_DIVE**
- Guardas:
  - `user_returned_early()` (voltou antes do agendado)
  - OU `followup_time_reached() AND user_engaged` (hora chegou e usuário respondeu)

**AWAITING_RETURN → CLOSED_NO_RESPONSE**
- Guarda: `timeout_hours > 48 AND no_user_messages`

**Qualquer estado → HANDOFF_HUMAN**
- Guardas (OU lógico):
  - `explicit_request_human`
  - `complex_requirement_detected` (Supervisor marca)
  - `supervisor_confidence < 0.5` (sistema perdido)
  - `loop_detected` (preso no mesmo estado por > 5 turnos)

**Qualquer estado → CLOSED_ABUSE**
- Guardas (OU lógico):
  - `abuse_metrics.is_malicious()`
  - `repeated_invalid_inputs > 5`
  - `cost_projection > hard_limit`

### 5.3 Reabertura de Estados Terminais

**CLOSED_SUCCESS → QUALIFYING**
- Guardas:
  - `days_since_close < 7`
  - `reopen_intent_detected` (Supervisor identifica)
  - Registra `reopen_reason` em auditoria

**CLOSED_UNQUALIFIED → QUALIFYING**
- Guardas:
  - `days_since_close < 30`
  - `situation_changed_signal` (ex: "agora temos budget")

**CLOSED_NO_RESPONSE → DEEP_DIVE**
- Guardas:
  - `days_since_close < 14`
  - Sistema restaura contexto anterior

**CLOSED_ABUSE → [bloqueado]**
- Requer aprovação humana via dashboard

---

## 6. Controle de Abuso e Custo

### 6.1 AbuseMetrics - Detecção de Comportamento Anômalo

**Métricas rastreadas por sessão:**

**Qualidade de Input:**
- `repeated_invalid_inputs` - Respostas tipo "teste", "aaa", "123", "asdasd"
- `semantic_noise_score` - Detector de gibberish via embedding distance
- `contradictory_info_count` - Usuário muda informação básica (nome diferente 2x)

**Velocidade Anômala:**
- `rapid_state_transitions` - Mais de 5 estados em menos de 2 minutos
- `message_frequency_spike` - Mais de 10 mensagens em 1 minuto
- `avg_response_time` - < 2s consistentemente = bot?

**Padrões de Exploração:**
- `repeated_context_switching` - Alterna entre produtos > 3x sem aprofundar
- `field_collection_resistance` - Nunca fornece informação válida após 5 tentativas
- `scheduling_loop` - Agenda e cancela > 2x

**Thresholds:**
```
is_suspicious() -> score > 30 pontos
is_malicious() -> score > 60 pontos

Pontuação:
- invalid_input: 5 pontos cada
- rapid_transition: 10 pontos cada
- semantic_noise > 0.8: 15 pontos
- contradictory_info: 20 pontos
```

**Ação ao detectar abuso:**
1. `is_suspicious()` - Log de alerta, continua operação mas com modelo mais barato (3.5 vs 4)
2. `is_malicious()` - Transição forçada para `CLOSED_ABUSE`, bloqueia por 24h

### 6.2 CostTracking - Visibilidade e Controle de Gastos

**Rastreamento por sessão:**

**Consumo:**
- `total_tokens_input` / `total_tokens_output`
- `total_cost_usd` (calculado em tempo real)
- `model_used` (atual)
- `llm_calls_count` (quantas chamadas foram feitas)

**Projeção:**
- `projected_cost_to_conversion` (vem do Supervisor)
- `cost_per_field_collected` (métrica de eficiência)

**Thresholds e Ações:**

```
Sessão nova: GPT-4 (qualidade máxima)

Se custo > $0.30: downgrade para GPT-3.5
Se custo > $0.50: downgrade para GPT-3.5-turbo (mais rápido/barato)
Se custo > $1.00: HANDOFF_HUMAN (algo está errado)
Se custo > $2.00: CLOSED_ABUSE (hard limit)
```

**Visibilidade no Dashboard:**
- Custo médio por lead qualificado
- Custo médio por agendamento
- ROI por contexto de negócio (SaaS vs Automação)
- Sessões com custo anômalo (> P95)

---

## 7. Migração do Sistema Atual

### 7.1 Estratégia: Migração Gradual com Validação Assistida por LLM

**Princípio:** Não inferir cegamente de `loaded_contexts` → validar contra histórico real.

#### Fase 1: Preparação (1 semana)

**Objetivo:** Adicionar campos novos sem quebrar sistema atual.

- Adicionar colunas à tabela de sessões:
  - `business_contexts_v2` (JSON array)
  - `primary_intent_v2` (string nullable)
  - `collected_fields_v2` (JSON object)
  - `fsm_version` (enum: 'v1' | 'v2')
  
- Sistema continua operando em `fsm_version='v1'`
- Dual-write: popula campos v2 em paralelo para análise

#### Fase 2: Migração com Validação LLM (2 semanas)

**Objetivo:** Migrar sessões ativas existentes com validação de contexto.

**Processo:**

Para cada sessão ativa:

1. **Inferência inicial** de `business_contexts` baseada em `loaded_contexts`

2. **Validação via LLM** contra histórico:
   ```
   Prompt para Supervisor:
   "Histórico das últimas 10 mensagens: [...]
   Contextos carregados pelo sistema: ['vertentes/saas/core.yaml', 'vertentes/automacao/workflows.yaml']
   Inferência automática: active_contexts={SAAS, AUTOMACAO}, primary_intent=SAAS
   
   Validação:
   1. A inferência está correta?
   2. Há ambiguidade que exige revisão humana?
   3. Quais campos podem ser extraídos retroativamente do histórico?
   
   Retorne JSON estruturado."
   ```

3. **Classificação do resultado:**
   - **Confiança alta (> 0.85):** Migra automaticamente
   - **Confiança média (0.6-0.85):** Migra mas marca para auditoria
   - **Confiança baixa (< 0.6):** Flag para revisão humana obrigatória

4. **Extração retroativa de campos:**
   - Supervisor analisa histórico e tenta preencher `collected_fields`
   - Campos extraídos retroativamente recebem `source='migration'` e `confidence` ajustado

**Estimativa:** 3000 sessões ativas × 2s por validação = ~100 min de processamento.

**Custo estimado:** 3000 validações × $0.01 = ~$30 (aceitável para garantir qualidade).

#### Fase 3: Teste A/B (2 semanas)

**Objetivo:** Validar que FSM v2 performa melhor que v1 em produção.

**Configuração:**
- 20% das sessões **novas** usam FSM v2
- 80% continuam em v1 (baseline)
- Sessões existentes permanecem em sua versão original (não migrar mid-conversation)

**Métricas comparativas:**

| Métrica | KPI v1 (baseline) | Meta v2 |
|---------|-------------------|---------|
| Taxa de perguntas repetidas | 35% | < 15% |
| Campos coletados/conversa | 2.1 | > 3.5 |
| Conversão para agendamento | 18% | > 25% |
| Tempo até qualificação | 8.3 min | < 6 min |
| Taxa de handoff humano | 42% | 28-32% |
| Custo médio por lead qualificado | $0.45 | < $0.40 |
| Sessões com abuso detectado | não medido | < 2% |

**Critério de sucesso:** 4 de 7 métricas melhoram significativamente (> 20%) sem degradação de outras.

#### Fase 4: Rollout Gradual (2 semanas)

**Objetivo:** Migrar 100% do tráfego para v2.

**Cronograma:**
- Semana 1: 50% v2, 50% v1
- Semana 2, dia 1-3: 80% v2, 20% v1
- Semana 2, dia 4-5: 95% v2, 5% v1
- Semana 2, dia 6-7: 100% v2

**Monitoramento contínuo:**
- Alertas automáticos se qualquer métrica degradar > 10%
- Rollback automático se latência P95 > 2s (vs 1.2s baseline)
- Dashboard de migração em tempo real

**Deprecação de v1:**
- Código v1 mantido por 60 dias para rollback de emergência
- Após 60 dias, remoção de código legado

---

## 8. Observabilidade e Auditoria

### 8.1 Logs Estruturados

**Cada transição de estado gera log completo:**

```
Campos obrigatórios:
- session_id, user_phone
- from_state, to_state, transition_trigger
- business_contexts (current), primary_intent
- collected_fields_count, missing_critical_fields
- supervisor_decision (reasoning, confidence)
- abuse_metrics (score, flags)
- cost_tracking (total, projection)
- timestamp, duration_in_previous_state
```

**Cada chamada LLM (Supervisor ou Content) gera log:**

```
Campos obrigatórios:
- session_id, llm_role (supervisor | content_gen)
- model_used, tokens_input, tokens_output, cost
- latency_ms, cache_hit (bool)
- prompt_template_version
- output_validation_passed (bool)
```

**Alertas automáticos:**
- Sessão presa no mesmo estado por > 5 turnos
- Custo de sessão > $1.50 (P99)
- Loop de transições detectado (A→B→A→B)
- Taxa de handoff humano > 45% em 1h (possível problema sistêmico)

### 8.2 Dashboard de Monitoramento

**Visão em Tempo Real:**
- Sessões ativas por estado (distribuição)
- Taxa de transição por minuto
- Custo acumulado na última hora
- Sessões com flags de abuso ativas

**Visão Analítica:**
- Funil de conversão (INITIAL → QUALIFYING → DEEP_DIVE → SCHEDULING)
- Tempo médio em cada estado
- Taxa de retorno por tipo de encerramento
- ROI por contexto de negócio
- Campos mais difíceis de coletar (> 3 tentativas)

**Visão de Qualidade:**
- Transições rejeitadas pelo Supervisor (motivo)
- Campos extraídos com baixa confiança (< 0.6)
- Sessões que reabriram (análise de padrões)
- Feedback humano pós-handoff

---

## 9. Requisitos Não-Funcionais

### 9.1 Performance

**Latência:**
- P50: < 800ms (tempo total de resposta ao usuário)
- P95: < 1.5s
- P99: < 2.5s

**Breakdown esperado:**
- Supervisor LLM: 400-600ms
- Content LLM: 300-500ms
- DB + validações: 100-200ms

**Otimizações:**
- Cache de templates compilados em memória
- Supervisor e Content podem rodar em paralelo quando aplicável
- Preload de contextos mais comuns (SAAS, AUTOMACAO)

### 9.2 Resiliência

**Fallbacks obrigatórios:**

1. **Supervisor falha:**
   - Sistema mantém estado atual
   - Usa Content LLM com prompt genérico
   - Loga erro para revisão
   - Após 2 falhas consecutivas → HANDOFF_HUMAN

2. **Content LLM falha:**
   - Tenta novamente com modelo alternativo (3.5 se estava em 4)
   - Após 2 falhas → resposta template pré-definida + HANDOFF_HUMAN

3. **DB write falha:**
   - Salva em cache local
   - Retry com backoff exponencial (3 tentativas)
   - Se persistir → HANDOFF_HUMAN com estado serializado em log

**Circuit breaker:**
- Se taxa de erro de qualquer componente > 20% em 5 min → pausa processamento de novas sessões por 2 min
- Alertas críticos para eng team

### 9.3 Segurança

**PII Protection:**
- Campos sensíveis (`email`, `telefone`, `cpf`) sempre marcados como PII
- Logs nunca contêm PII em plaintext (hash SHA256)
- Retenção: PII deletado após 90 dias de inatividade (LGPD compliance)

**Rate Limiting:**
- Por telefone: max 50 mensagens/hora (proteção contra spam)
- Por sessão: max 100 turnos (após isso → HANDOFF_HUMAN)
- Global: se load > 80% capacidade → throttle criação de novas sessões

**Auditoria:**
- Toda decisão do Supervisor é auditável (reasoning explícito)
- Reabertura de `CLOSED_ABUSE` gera notificação para compliance
- Modificação manual de sessão (via dashboard) registra quem/quando/por quê

---

## 10. Casos de Uso Complexos Resolvidos

### 10.1 Usuário com Interesse Híbrido

**Cenário:**
"Quero SaaS para delivery mas também preciso integrar com automação de marketing que vocês fazem"

**FSM v1 (atual):** Forçaria escolha, perderia informação

**FSM v2:**
```
active_contexts = {SAAS, AUTOMACAO}
primary_intent = None  # Supervisor detecta ambiguidade
collected_fields['interesse_detalhado'] = "SaaS delivery + integração marketing automation"

Próximo estado: QUALIFYING (aprofundar para definir primary_intent)
```

### 10.2 Lead Desqualificado que Retorna

**Cenário:**
- Dia 1: Lead fala sobre SaaS, descobre que budget é muito baixo → `CLOSED_UNQUALIFIED`
- Dia 15: "Conseguimos aprovar orçamento, quero retomar"

**FSM v1:** Inicia do zero, repete toda qualificação

**FSM v2:**
```
Reabertura detectada (dentro da janela de 30 dias)
Sistema restaura:
- active_contexts = {SAAS}
- collected_fields = {nome, email, empresa, [... tudo que já tinha]}
- disqualification_reason = 'fora_do_budget'  # mantido para contexto

Supervisor ajusta prompt:
"Você já conversou com [nome] da [empresa]. Anteriormente o budget era insuficiente,
mas agora eles retornaram dizendo que conseguiram aprovação. Foque em confirmar
novo budget e avançar para agendamento."

Transição: CLOSED_UNQUALIFIED → DEEP_DIVE (não volta para QUALIFYING)
```

### 10.3 Usuário Abusivo Tentando Explorar Sistema

**Cenário:**
```
Msg 1: "quero saas"
Msg 2: "teste"
Msg 3: "aaa"
Msg 4: "123"
Msg 5: "asdasd"
[...]
```

**FSM v1:** Continua respondendo, queima tokens indefinidamente

**FSM v2:**
```
Após msg 4:
abuse_metrics.repeated_invalid_inputs = 3
abuse_metrics.semantic_noise_score = 0.85
abuse_score = 35 (is_suspicious)

Ação: Downgrade para GPT-3.5, adiciona validação mais restritiva

Após msg 6:
abuse_score = 65 (is_malicious)

Ação: Transição forçada para CLOSED_ABUSE
Resposta: "Detectamos um padrão de uso inadequado. Caso precise de atendimento real,
entre em contato através do email contato@pyloto.com"

Telefone bloqueado por 24h.
```

### 10.4 Loop Infinito de Estado

**Cenário:**
Sistema fica preso em `DEEP_DIVE` → `QUALIFYING` → `DEEP_DIVE` sem progredir

**FSM v2 - Proteção:**
```
transition_history = [
    (DEEP_DIVE, timestamp1),
    (QUALIFYING, timestamp2),
    (DEEP_DIVE, timestamp3),
    (QUALIFYING, timestamp4),
    (DEEP_DIVE, timestamp5)  # 3ª vez em DEEP_DIVE
]

Detector de loop ativado após 5 turnos:
loop_detected = True

Ação: Transição forçada para HANDOFF_HUMAN
Reasoning: "Sistema incapaz de qualificar ou aprofundar adequadamente. Escalando para humano."
```

### 10.5 Agendamento com Múltiplos Cancelamentos

**Cenário:**
- Usuário agenda para terça
- Cancela
- Agenda para quinta
- Cancela novamente

**FSM v2 - Detecção:**
```
collected_fields['scheduling_history'] = [
    {'data': '2026-02-18', 'status': 'canceled', 'reason': 'conflito agenda'},
    {'data': '2026-02-20', 'status': 'canceled', 'reason': None}
]

abuse_metrics.scheduling_loop = 2

Se tentar cancelar 3ª vez:
→ Supervisor detecta padrão
→ Sugere HANDOFF_HUMAN: "Percebo que há dificuldade em definir uma data. Gostaria que um consultor humano entrasse em contato para alinhar melhor sua disponibilidade?"
```

---

## 11. Métricas de Sucesso e Critérios de Validação

### 11.1 KPIs Quantitativos (Mínimo Viável)

**Critério de aprovação: melhorar 4 de 7 métricas em > 20% sem degradar outras**

| Métrica | Baseline v1 | Meta v2 | Método de Medição |
|---------|-------------|---------|-------------------|
| Taxa de perguntas repetidas | 35% | < 15% | Análise de similaridade semântica entre perguntas |
| Campos únicos coletados/conversa | 2.1 | > 3.5 | Contagem de `collected_fields` ao final |
| Taxa de conversão para agendamento | 18% | > 25% | % de sessões que atingem `SCHEDULED_FOLLOWUP` |
| Tempo médio até qualificação | 8.3 min | < 6 min | Tempo entre `INITIAL` e `DEEP_DIVE` |
| Taxa de handoff para humano | 42% | 28-32% | % de sessões em `HANDOFF_HUMAN` |
| Custo médio por lead qualificado | $0.45 | < $0.40 | `total_cost_usd` / leads em `DEEP_DIVE` |
| Taxa de sessões com abuso | não medido | < 2% | % de sessões em `CLOSED_ABUSE` |

### 11.2 KPIs Qualitativos

**Avaliação via survey pós-interação (NPS):**

| Dimensão | Meta |
|----------|------|
| "A conversa foi fluida e não repetitiva" | > 7.5/10 |
| "O sistema entendeu minha necessidade" | > 7.0/10 |
| "Não precisei repetir informações" | > 8.0/10 |
| NPS geral | > 40 |

**Avaliação via análise humana (amostra 100 conversas):**
- % de conversas onde contexto foi mantido corretamente: > 90%
- % de transições de estado corretas: > 85%
- % de campos extraídos com alta confiança (> 0.8): > 70%

### 11.3 Critérios de Rollback

**Rollback obrigatório se qualquer condição:**

1. **Degradação crítica de performance:**
   - P95 latência > 3s por > 10 minutos
   - Taxa de erro > 5% por > 5 minutos

2. **Degradação de negócio:**
   - Taxa de conversão cai > 30% vs baseline
   - Taxa de handoff sobe > 50%
   - NPS cai > 15% vs baseline

3. **Incidentes de segurança:**
   - Vazamento de PII detectado
   - Taxa de falsos positivos de abuso > 10%

4. **Instabilidade sistêmica:**
   - > 5% de sessões em loop infinito
   - Custo médio por sessão > $2.00 (hard limit)

---

## 12. Riscos, Mitigações e Trade-offs

### Risco 1: Complexidade Arquitetural Aumenta Superfície de Bugs

**Descrição:** FSM v2 tem mais componentes (Supervisor, validações, guardas complexas) = mais pontos de falha

**Probabilidade:** Alta  
**Impacto:** Médio

**Mitigação:**
- Testes unitários obrigatórios para cada função de guarda (cobertura > 90%)
- Testes de integração end-to-end para fluxos principais (5 cenários críticos)
- Feature flags para desabilitar componentes isoladamente (ex: desligar Supervisor, voltar para guardas simples)
- Monitoramento granular de cada componente com alertas independentes

**Trade-off aceito:** Complexidade controlada em troca de capacidade de evolução

### Risco 2: Supervisor LLM Adiciona Latência

**Descrição:** 400-600ms de Supervisor pode degradar UX se não otimizado

**Probabilidade:** Média  
**Impacto:** Alto (UX)

**Mitigação:**
- Paralelização quando possível (Supervisor + Content LLM em paralelo se decisão de estado for trivial)
- Cache agressivo de decisões para contextos similares (ex: "INITIAL + primeira mensagem genérica" quase sempre vai para QUALIFYING)
- Timeout de 800ms no Supervisor (se ultrapassar, usa fallback determinístico)
- Monitoramento P95 de latência com alertas se > 1.5s

**Trade-off aceito:** +300ms de latência em troca de qualidade de decisão

### Risco 3: Prompts Compostos Criam Inconsistências

**Descrição:** Blocos independentes podem conflitar quando mesclados (ex: `tone.yaml` diz "seja formal", `context/SAAS.yaml` diz "seja casual")

**Probabilidade:** Média  
**Impacto:** Médio (qualidade)

**Mitigação:**
- Validador automático de prompts compostos (roda em CI/CD)
- Template de teste: gera 10 exemplos de cada combinação (flow × context) e valida que não há contradições
- Revisão humana obrigatória antes de merge de novos blocos
- Versionamento de blocos (se `tone.yaml` muda, força re-teste de todas combinações)

**Trade-off aceito:** Risco de inconsistência pontual em troca de escalabilidade de manutenção

### Risco 4: Migração Corrompe Sessões Ativas

**Descrição:** Inferência de contexto de sessões mid-conversation pode gerar estados inválidos

**Probabilidade:** Baixa (mitigado por validação LLM)  
**Impacto:** Alto (perda de leads ativos)

**Mitigação:**
- Validação assistida por LLM (não migração cega)
- Flag de auditoria para sessões migradas com confiança < 0.85
- Rollback individual de sessão (se usuário reportar problema, restaura estado v1)
- Migração fora de horário de pico (madrugada) para minimizar impacto

**Trade-off aceito:** Risco pequeno de corrupção em troca de não ter sistema dual permanentemente

### Risco 5: Falsos Positivos de Abuso Bloqueiam Usuários Legítimos

**Descrição:** Usuário com comportamento atípico (ex: muito rápido, respostas curtas legítimas) pode ser classificado como abusivo

**Probabilidade:** Média  
**Impacto:** Alto (perda de lead real)

**Mitigação:**
- Threshold conservador para `CLOSED_ABUSE` (score > 60, não 50)
- Estado intermediário `SUSPECTED_ABUSE` que adiciona friction mas não bloqueia (ex: adiciona captcha, limita taxa)
- Dashboard de revisão de bloqueios (eng/comercial pode reverter manualmente)
- Coleta de feedback: "Você foi bloqueado por engano? Clique aqui" → cria ticket para revisão

**Trade-off aceito:** Preferir falso negativo (deixar abusivo passar) do que falso positivo (bloquear lead real)

### Risco 6: Custo de Operação Aumenta (Supervisor + Validações)

**Descrição:** Adicionar Supervisor LLM aumenta custo por sessão

**Probabilidade:** Alta (certeza)  
**Impacto:** Médio (financeiro)

**Estimativa:**
```
Custo médio v1: $0.45/lead qualificado
Custo adicional Supervisor: +$0.08/lead (GPT-4 para decisões)
Custo médio v2: ~$0.53/lead

Aumento: 17%
```

**Mitigação:**
- Downgrade inteligente: se sessão já está bem encaminhada (coletou 5+ campos, high confidence), Supervisor pode ser GPT-3.5
- Cache de decisões: contextos muito similares reusam decisão anterior
- ROI esperado: se conversão aumenta de 18% para 25%, custo por conversão real cai

**Cálculo de ROI:**
```
v1: $0.45 / 0.18 = $2.50 por conversão
v2: $0.53 / 0.25 = $2.12 por conversão

Economia líquida: -15% no custo por conversão apesar de 17% mais caro por lead
```

**Trade-off aceito:** Investir 17% mais por lead para reduzir 15% custo por conversão

---

## 13. Próximos Passos e Roadmap

### Sprint 1: Fundação (1 semana)

**Objetivo:** Criar estruturas de dados e enums

**Entregas:**
- Novos enums (`FlowState`, `BusinessContext`)
- Modelo `SessionFSM` completo
- Modelo `AbuseMetrics` e `CostTracking`
- Schema de banco atualizado (migration script)

**Responsável:** Backend Lead  
**Critério de aceite:** Testes unitários passando, schema validado em staging

### Sprint 2: Matriz de Transições (1 semana)

**Objetivo:** Implementar lógica de transições e guardas

**Entregas:**
- Arquivo `v2_transitions.py` com todas as guardas
- Testes unitários para cada função de guarda
- Detector de loops e circuit breaker
- Lógica de reabertura de estados terminais

**Responsável:** Backend + QA  
**Critério de aceite:** Cobertura de testes > 90%, edge cases documentados

### Sprint 3: Supervisor LLM (2 semanas)

**Objetivo:** Implementar cérebro decisório do sistema

**Entregas:**
- Service `SupervisorLLM` com todas as responsabilidades
- Prompts estruturados para Supervisor
- Schemas Pydantic para outputs do Supervisor
- Fallbacks e circuit breakers
- Testes de integração com LLM mockada

**Responsável:** AI/ML Lead  
**Critério de aceite:** Latência P95 < 600ms, taxa de erro < 1% em testes

### Sprint 4: Sistema de Prompts Compostos (1 semana)

**Objetivo:** Criar hierarquia de templates e composição

**Entregas:**
- Estrutura de diretórios `prompts/base/`, `prompts/flow/`, `prompts/context/`
- Blocos essenciais: tone, safety, format, field_validation
- Blocos de flow: QUALIFYING, DEEP_DIVE, SCHEDULING
- Blocos de context: SAAS, AUTOMACAO, ENTREGAS
- Loader com composição dinâmica
- Validador de prompts (CI/CD)

**Responsável:** AI/ML + DevOps  
**Critério de aceite:** 15 blocos criados, validador integrado em CI

### Sprint 5: Migração e Validação (2 semanas)

**Objetivo:** Migrar sessões existentes com validação LLM

**Entregas:**
- Script `migrate_fsm_v2.py` com validação assistida
- Dashboard de acompanhamento de migração
- Lógica de dual-write (v1 + v2 em paralelo)
- Extração retroativa de `collected_fields`

**Responsável:** Backend + AI/ML  
**Critério de aceite:** 95% das sessões migradas com confiança > 0.6

### Sprint 6: Observabilidade (1 semana)

**Objetivo:** Logs, métricas e dashboard

**Entregas:**
- Logs estruturados para transições e LLM calls
- Dashboard de monitoramento em tempo real
- Alertas configurados (latência, erro, custo)
- Sistema de auditoria (PII hash, reasoning explícito)

**Responsável:** DevOps + Backend  
**Critério de aceite:** Dashboard acessível, alertas testados

### Sprint 7-8: Teste A/B e Rollout (2 semanas)

**Objetivo:** Validar v2 em produção e migrar 100%

**Entregas:**
- Feature flag para alternar v1/v2
- Pipeline de testes A/B (20% v2)
- Coleta de métricas comparativas
- Rollout gradual (50% → 80% → 100%)
- Documentação pós-mortem

**Responsável:** Eng Lead + Product  
**Critério de aceite:** 4 de 7 KPIs melhoram > 20%, rollout completo sem rollback

### Sprint 9: Otimização e Hardening (1 semana)

**Objetivo:** Refinar baseado em dados reais

**Entregas:**
- Ajuste de thresholds (abuse, custo, confiança)
- Otimizações de performance identificadas
- Documentação técnica completa
- Deprecação de código v1

**Responsável:** Full Team  
**Critério de aceite:** P95 latência < 1.5s, custo médio < $0.45

**Timeline total:** 11 semanas (vs 5 na proposta original)

---

## 14. Conclusão e Decisão Requerida

### Transformação Proposta

Esta arquitetura transforma a FSM de **controle técnico de fluxo** em **sistema contextualmente consciente com supervisão inteligente** através de:

1. **Estados Compostos:** `(FlowState × Set<BusinessContext> × CollectedFields)`
2. **Supervisor LLM:** Orquestrador mestre que decide, valida e projeta
3. **Prompts Compostos:** Escalabilidade de manutenção (15 blocos vs 36+ arquivos)
4. **Controle de Abuso:** Detecção e mitigação proativa de comportamento anômalo
5. **Rastreamento de Custo:** Visibilidade total e controle por sessão
6. **Reabertura Controlada:** Estados terminais não são permanentes
7. **Auditoria Completa:** Toda decisão é rastreável e justificável

### Trade-offs Explícitos

| Aspecto | v1 (atual) | v2 (proposto) |
|---------|-----------|---------------|
| **Complexidade** | Baixa (estados simples) | Média (componentes especializados) |
| **Latência** | ~500ms | ~800ms (+300ms do Supervisor) |
| **Custo por lead** | $0.45 | $0.53 (+17%) |
| **Custo por conversão** | $2.50 | $2.12 (-15%) |
| **Manutenibilidade** | Baixa (tudo acoplado) | Alta (componentes isolados) |
| **Qualidade de decisão** | Heurística | Supervisionada por LLM |
| **Resiliência a abuso** | Inexistente | Proativa com métricas |
| **Capacidade de evolução** | Limitada | Alta (novos contextos isolados) |

### Riscos Residuais Após Mitigações

**Aceitáveis:**
- Complexidade controlada vs capacidade de evolução
- +300ms latência vs qualidade de decisão
- +17% custo por lead vs -15% custo por conversão

**Monitorar ativamente:**
- Falsos positivos de abuso (dashboard de revisão obrigatório)
- Inconsistências de prompts compostos (validador em CI)
- Supervisão adicional nas primeiras 4 semanas pós-rollout

### Decisão Requerida

**Pergunta para stakeholders:**

**Aprovar implementação da FSM v2 conforme especificado?**

**Se SIM:**
- Timeline: 11 semanas até rollout completo
- Budget adicional: ~$8k (migração + testes + eng time)
- Risco: Médio (mitigado por rollout gradual e rollback disponível)
- Retorno esperado: Conversão +39% (18% → 25%), satisfação +20% (NPS)

**Se NÃO:**
- Manter v1 atual
- Implementar apenas melhorias pontuais (cache de contextos, logs melhores)
- Aceitar limitações conhecidas (repetição, sem controle de abuso, contexto perdido)

**Se MODIFICAR:**
- Especificar quais componentes manter/remover
- Re-calcular timeline e trade-offs

---

**Decisão final aguardando aprovação de:** Eng Lead, Product Owner, CTO
