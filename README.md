# Atende Pyloto - Sistema de Atendimento IA via WhatsApp

**Status:** Em desenvolvimento ativo - Refatoração para arquitetura Otto (agente único + utilitários)

Este repositório implementa um sistema de atendimento automatizado para WhatsApp usando IA conversacional (OpenAI GPT-4), com foco em qualificação de leads B2B para a Pyloto.

---

## Arquitetura

### Visão Geral 'Quebra-Gelo' e 'comandos'

Estão configuradas/cadastradas as seguintes mensagens de quebra gelo e comandos "/" no
painel da Meta (Whatsapp Business API):
  **Quebra-gelos**
    - Como funciona a Gestão de perfis e Tráfego?
    - Como funciona a Automação?
    - Como funciona o desenvolvimento de Sistemas Sob Medida?
    - O que é o SaaS da Pyloto?
  **comandos**
    - `/automacao` - Serviço de automação de atendimento com ou sem IA. Entregamos um painel de gestão onde é possível "assumir" uma conversa que esta sendo atendida pelo Bot ou IA, bem como visualizar os atendimentos em andamento.
    - `/sobmedida`- Nós realizamos um estudo detalhado do fluxo atual do cliente, ferramentas que são utilizadas e serviços que podem ser integrados. Entregamos uma plataforma (Web ou Local) pensada exclusivamente para atender todas as necessidades.
    - `/entregas_servicos`- Pyloto Serviços é o carro chefe da Pyloto. Realizamos a intermediação operacional entre prestadores de serviço cadastrados e solicitantes (PF ou PJ). Solicitações devem ser realizadas exclusivamente através do whatsapp +554291619261.
    - `/saas`- "O Pyloto da sua comunicação". O SaaS da Pyloto, pensado para atender a maior parte dos nichos e empresas de maneira adaptável.

Para as mensagens de "Quebra-gelos" e "comandos", deveremos cadastrar uma resposta fixa, a qual deverá constar no {conversation_history} porém, não deverá passar por nenhum dos agentes, essas serão respostas fixas.

### Visão Geral LLMs

O sistema utiliza **arquitetura de agente único (Otto) + agentes utilitários**, substituindo o pipeline sequencial de 4 agentes LLM por uma abordagem mais eficiente:

```Fluxo

┌──────────────────────────────────────────────────────────────┐
│                    INCOMING MESSAGE                           │
└───────────────────────┬──────────────────────────────────────┘
│
┌───────────┴───────────┐
│ TranscriptionAgent    │ (se áudio, 30% msgs)
│ Whisper API: 500-1200ms│
└───────────┬───────────┘
│
┌───────────────┴──────────────────┐
│  PARALLEL EXECUTION              │
│  ┌─────────────┬──────────────┐  │
│  │ OttoAgent   │ ExtractionAgent│ │
│  │ Decide +    │ Extrai dados │  │
│  │ Responde    │ estruturados │  │
│  │ 1200-1800ms │ 400-800ms    │  │
│  └──────┬──────┴──────┬───────┘  │
└─────────┼─────────────┼──────────┘
│             │
▼             ▼
OttoDecision  ExtractedLeadInfo
│             │
└──────┬──────┘
│
┌────────────┴──────────────┐
│ Merge → LeadContact       │
│ (atualiza perfil do lead) │
└────────────┬───────────────┘
│
┌────────────┴──────────────┐
│ ValidationPipeline        │
│ 3-gate: Determinístico +  │
│ Confidence + LLM Review   │
└────────────┬───────────────┘
│
┌──────┴──────┐
│ Approved?   │
└──────┬──────┘
│
YES  │  NO
┌───────┴───────┐
│               │
▼               ▼
SEND MESSAGE    ESCALA HUMANO

```

### Componentes Principais

#### 1. **OttoAgent** (Agente Principal)

- **Responsabilidade:** Decisão de estado FSM + geração de resposta + seleção de tipo de mensagem (tudo em 1 chamada LLM)
- **Modelo:** `gpt-5.1` (structured outputs)
- **Latência:** 1200-1800ms
- **Output:** `OttoDecision` (Pydantic structured)
  - `next_state`: Próximo estado FSM
  - `response_text`: Resposta natural (max 500 chars)
  - `message_type`: `text` | `interactive_button` | `interactive_list`
  - `confidence`: 0.0-1.0

#### 2. **ExtractionAgent** (Utilitário)

- **Responsabilidade:** Extrair informações estruturadas para preencher `LeadContact`
- **Modelo:** `gpt-5.1-mini` (barato e rápido)
- **Latência:** 400-800ms
- **Execução:** Paralelo com OttoAgent (não aumenta latência)
- **Output:** `ExtractedLeadInfo`
  - Dados pessoais: nome, email, telefone, empresa, cargo
  - Interesse: `primary_interest` (saas, sob_medida, gestao_perfis_trafego, automacao_atendimento, intermediacao_entregas) # apenas 1
  - Outros interesses: `others_interest` (sob_medida + automacao_atendimento) # até 3
  - Qualificação: urgência, necessidade específica, budget

#### 3. **TranscriptionAgent** (Utilitário)

- **Responsabilidade:** Transcrever áudios do WhatsApp para texto
- **Modelo:** Whisper API (OpenAI)
- **Latência:** 500-1200ms (30% das mensagens)
- **Execução:** Antes do pipeline principal (bloqueante)

#### 4. **ContextInjector** (Serviço)

- **Responsabilidade:** Injetar contexto dinâmico por vertente Pyloto
- **Lógica:** Lê `LeadContact.primary_interest` → Injeta contexto vertical relevante
- **Contextos:** 5 verticais (SaaS, Sob Medida, Gestao Perfis + Trafego, Automacao Atendimento, Intermediacao Entregas)
- **Economia:** 70% de tokens (injeta apenas contexto relevante vs todos contextos)

#### 5. **DecisionValidator** (Pipeline Híbrido)

- **Gate 1 - Determinístico (sempre):** Valida FSM, PII, promessas proibidas
- **Gate 2 - Confidence Check:** >= 0.85 aprova | < 0.7 escala | 0.7-0.85 → Gate 3
- **Gate 3 - LLM Review (seletivo):** Validação leve com `gpt-5.1-mini` apenas em zona cinza

---

## Estrutura do Repositório (`src/`)

A estrutura é o **contrato de organização**. Cada pasta tem papel claro; arquivos fora do lugar viram dívida técnica.

```tree

src/
├── ai/                    \# Inteligência (LLM, prompts, agentes)
├── api/                   \# Interface/Edge (webhooks, adapters)
├── app/                   \# Aplicação (casos de uso, orquestração)
├── config/                \# Configuração e settings
├── fsm/                   \# Máquina de estados (domínio)
└── utils/                 \# Utilitários cross-cutting

```

### `src/ai/` — Inteligência

**Escopo:** LLM, prompts, agentes e validações de IA.  
**Proibido:** Importar `api/` ou fazer IO direto (rede/banco).

```tree

ai/
├── contexts/              \# Contextos por vertente Pyloto
│   ├── __init__.py
│   └── pyloto_verticals.py  \# SAAS_CONTEXT, SOB_MEDIDA_CONTEXT, etc
├── models/                \# DTOs de entrada/saída
│   ├── extraction.py      \# ExtractedLeadInfo
│   ├── otto_decision.py   \# OttoDecision
│   └── validation.py      \# ValidationResult, QualityAssessment
├── services/              \# Agentes e serviços de IA
│   ├── otto_agent.py           \# Agente principal (único)
│   ├── extraction_agent.py     \# Extração de dados estruturados
│   ├── transcription_agent.py  \# Transcrição de áudios
│   ├── context_injector.py     \# Injeção de contexto dinâmico
│   ├── decision_validator.py   \# Pipeline de validação 3-gate
│   ├── response_quality_agent.py    \# [FASE 2] Auto-QA de respostas
│   ├── intent_clarification_agent.py \# [FASE 2] Desambiguação
│   ├── conversation_summary_agent.py \# [FASE 3] Sumarização
│   └── handoff_preparation_agent.py  \# [FASE 3] Briefing handoff
└── utils/                 \# Helpers de IA
├── parsers.py         \# Parsers de output LLM (se necessário)
└── prompt_utils.py    \# Helpers de formatação de prompts

```

**Regras:**

- Cada agente: 1 arquivo ≤ 200 linhas (§4 REGRAS_E_PADROES.md)
- Structured outputs com Pydantic (§7)
- Logs estruturados sem PII (§6)
- Type hints completos (§5)

---

### `src/api/` — Interface/Edge

**Escopo:** Camada de borda, webhooks, adapters de canais.  
**Responsabilidade:** Receber requests, validar assinatura, normalizar payload.  
**Proibido:** Decisão de FSM, regras de sessão, orquestração de casos de uso.

```tree

api/
├── connectors/
│   └── whatsapp/          \# Conector WhatsApp Cloud API
│       ├── webhook/       \# Receber/verificar webhook
│       ├── inbound/       \# Normalização de eventos inbound
│       ├── outbound/      \# Envio de mensagens outbound
│       ├── http_client.py \# Cliente HTTP WhatsApp API
│       ├── signature.py   \# Validação de assinatura
│       └── message_builder.py  \# Construção de payloads
├── normalizers/           \# Normalizadores por fornecedor
│   └── graph_api/         \# Meta Graph API
├── payload_builders/      \# Builders de payload por destino
└── validators/            \# Validações por canal/protocolo

```

---

### `src/app/` — Aplicação

**Escopo:** Coração do sistema - coordena regras, FSM, IA e infraestrutura.  
**Padrão mental:** `app` executa | `api` adapta | `ai` decide | `fsm` governa | `utils` apoia

```tree

app/
├── bootstrap/             \# Composition root (DI, wiring)
│   ├── __init__.py
│   └── whatsapp_factory.py  \# Factory de componentes WhatsApp
├── use_cases/             \# Casos de uso (inputs/outputs)
│   └── whatsapp/
│       ├── process_inbound_canonical.py  \# Use case principal
│       └── _inbound_helpers.py           \# Helpers (merge_extracted_info)
├── protocols/             \# Contratos/interfaces
│   ├── models.py          \# LeadContact, Session, InboundEvent, OutboundCommand
│   ├── repositories.py    \# Interfaces de repositórios
│   └── services.py        \# Interfaces de serviços externos
├── infra/                 \# Implementações concretas de IO
│   ├── repositories/      \# Firestore, Redis
│   ├── http/              \# Clients HTTP (WhatsApp API, OpenAI)
│   └── secrets/           \# Secret Manager
├── sessions/              \# Gerenciamento de sessões
│   ├── manager.py         \# SessionManager
│   └── models.py          \# Session, LeadContact
├── policies/              \# Políticas (rate limit, abuse, retry)
├── observability/         \# Logs, tracing, métricas
└── constants/             \# Constantes da aplicação

```

**Modelo de Dados Principal:**

#### `LeadContact` (Single Source of Truth do Lead)

```python
class ContactCard(BaseModel):
    """Perfil do lead armazenado no Firestore."""

    # DO WEBHOOK (sempre disponível)
    wa_id: str              # WhatsApp ID único (= phone)
    phone: str              # Número com código país (5544988887777)
    whatsapp_name: str      # Nome salvo no WhatsApp do usuário (Não necessáriamente será o nome verdadeiro)

    # EXTRAÍDOS (progressivamente pelo ExtractionAgent)
    full_name: str | None              # Nome completo real
    email: str | None                  # Email
    company: str | None                # Empresa
    role: str | None                   # Cargo
    location: str | None               # Cidade/Estado

    # INTERESSE (crítico para context injection)
    primary_interest: Literal[
        "saas", "sob_medida", "gestao_perfis_trafego",
        "automacao_atendimento", "intermediacao_entregas"
    ] | None
    secondary_interests: list[str]

    # QUALIFICAÇÃO
    urgency: Literal["low", "medium", "high", "urgent"] | None
    budget_indication: str | None
    specific_need: str | None
    company_size: Literal["mei", "micro", "pequena", "media", "grande"] | None

    # SCORES (calculados automaticamente)
    qualification_score: float = 0.0    # 0-100
    is_qualified: bool = False          # True se >= 60

    # METADADOS
    first_contact_at: datetime
    last_updated_at: datetime
    total_messages: int

    # FLAGS
    requested_human: bool = False
    showed_objection: bool = False
    was_notified_to_team: bool = False
```

**Storage:** Firestore collection `contact_card`, Document ID = `wa_id`

---

### `src/config/` — Configuração

**Escopo:** Settings tipados, carregamento de env, defaults, validação.

```tree
config/
├── settings/              # Settings por componente
│   ├── ai/
│   │   ├── openai.py      # OpenAI API key, model, timeout
│   │   └── validation.py  # Thresholds de validação
│   ├── whatsapp/
│   │   └── api.py         # WhatsApp token, phone_number_id
│   └── database/
│       ├── firestore.py   # Firestore project_id
│       └── redis.py       # Redis URL
└── logging/               # Configuração de logging
    └── setup.py           # Logging estruturado (JSON)
```

---

### `src/fsm/` — Máquina de Estados

**Escopo:** Estados, transições e regras determinísticas (domínio puro).

```tree
fsm/
├── states/
│   └── session.py         # SessionState (enum)
├── transitions/
│   └── rules.py           # VALID_TRANSITIONS (dict)
└── manager/
    └── fsm_manager.py     # Validação e aplicação de transições
```

**Estados FSM (10 fixos):**

```python
class SessionState(Enum):
    INITIAL = "INITIAL"                         # Primeira interação
    TRIAGE = "TRIAGE"                           # Identificando necessidade
    COLLECTING_INFO = "COLLECTING_INFO"         # Coletando dados do lead
    GENERATING_RESPONSE = "GENERATING_RESPONSE" # Respondendo dúvida
    HANDOFF_HUMAN = "HANDOFF_HUMAN"             # Escalou para humano
    SELF_SERVE_INFO = "SELF_SERVE_INFO"         # Info self-service (FAQ)
    SCHEDULED_FOLLOWUP = "SCHEDULED_FOLLOWUP"   # Agendou follow-up
    ROUTE_EXTERNAL = "ROUTE_EXTERNAL"           # Roteou para sistema externo
    TIMEOUT = "TIMEOUT"                         # Timeout de inatividade
    ERROR = "ERROR"                             # Erro técnico
```

---

### `src/utils/` — Utilitários

**Escopo:** Helpers genéricos (cross-cutting, sem regra de negócio).

```tree
utils/
├── errors/
│   └── exceptions.py      # Exceções customizadas
├── ids.py                 # Geração de IDs/fingerprints
├── audit.py               # Helpers de auditoria (sem PII)
└── timing.py              # Medições de latência
```

---

## Pipeline de Processamento

### Fluxo Completo (Detalhado)

```python
# src/app/use_cases/whatsapp/process_inbound_canonical.py

async def execute(self, event: InboundEvent) -> OutboundCommand:
    """Pipeline canônico de processamento."""

    # 1. LOAD SESSION (Firestore com cache Redis)
    session = await self.session_manager.resolve_or_create(event.sender_id)
    # Latência: 10ms (cache hit) ou 150ms (Firestore)

    # 2. FAST-PATH (70% dos casos)
    fast_result = self._classify_fast_path(event.message_text)
    if fast_result:
        return OutboundCommand(text=fast_result.response, message_type="text")
    # Latência total fast-path: ~200ms ✅

    # 3. TRANSCRIÇÃO (se áudio)
    if event.message_type == "audio":
        transcription = await self.transcription_agent.transcribe(
            audio_file_url=event.media_url,
            language="pt"
        )
        if transcription.confidence < 0.6:
            return OutboundCommand(text="Não consegui entender o áudio...")
        event.message_text = transcription.text
    # Latência: +500-1200ms (apenas 30% msgs)

    # 4. PARALLEL: Otto + Extraction
    decision, extracted = await asyncio.gather(
        self.otto.process_message(
            user_input=event.message_text,
            session=session,
            current_state=session.current_state
        ),
        self.extraction.extract(
            user_message=event.message_text
        )
    )
    # Latência: MAX(1800ms, 800ms) = 1800ms

    # 5. MERGE: Extracted → LeadContact
    session.lead_contact = merge_extracted_info(
        lead=session.lead_contact,
        extracted=extracted
    )
    session.lead_contact.calculate_qualification_score()
    # Latência: +10ms

    # 6. VALIDATION (3-gate)
    validation = await self.validator.validate(
        decision=decision,
        session=session,
        current_state=session.current_state
    )
    # Latência: 10ms (maioria) ou 500ms (zona cinza)

    if not validation.approved:
        if validation.validation_type == ValidationType.HUMAN_REQUIRED:
            await self.notify_human_team(session, decision)
            return OutboundCommand(
                text="Vou conectar você com nossa equipe!",
                next_state=SessionState.HANDOFF_HUMAN
            )

        # Aplica correções
        if validation.corrections:
            for field, value in validation.corrections.items():
                setattr(decision, field, value)

    # 7. UPDATE SESSION
    session.current_state = decision.next_state
    session.add_to_history(event.message_text, role="user")
    session.add_to_history(decision.response_text, role="assistant")
    await self.session_manager.save(session)
    # Latência: +100ms

    # 8. NOTIFICAR TIME (se qualificou)
    if session.lead_contact.is_qualified and not session.metadata.get("notified"):
        await self.notify_qualified_lead(session.lead_contact, session)
        session.metadata["notified"] = True

    # 9. RETURN
    return OutboundCommand(
        text=decision.response_text,
        message_type=decision.message_type,
        next_state=decision.next_state,
        metadata={
            "confidence": decision.confidence,
            "qualification_score": session.lead_contact.qualification_score
        }
    )
```

---

## Métricas e Performance

### Latência por Cenário

| Cenário                        | Frequência | P50   | P95   | Notas                 |
| :----------------------------- | :--------- | :---- | :---- | :-------------------- |
| **Fast-Path** (saudações, FAQ) | 70%        | 200ms | 350ms | Determinístico        |
| **Texto Simples**              | 20%        | 2.0s  | 2.5s  | Otto + Extraction     |
| **Texto + QA**                 | 8%         | 2.5s  | 3.2s  | +ResponseQualityAgent |
| **Áudio**                      | 30%        | 3.0s  | 3.5s  | +Transcrição          |
| **Áudio + QA**                 | 2%         | 3.5s  | 4.2s  | Pior caso             |

**SLA:** P95 < 4s (95% das respostas em menos de 4 segundos)

### Custo por Mensagem

| Componente                | Modelo      | Custo     | Frequência | Custo Médio       |
| :------------------------ | :---------- | :-------- | :--------- | :---------------- |
| OttoAgent                 | gpt-4o      | \$0.0025  | 30%        | \$0.00075         |
| ExtractionAgent           | gpt-4o-mini | \$0.00015 | 30%        | \$0.000045        |
| TranscriptionAgent        | Whisper     | \$0.001   | 30%        | \$0.0003          |
| ValidationPipeline Gate 3 | gpt-4o-mini | \$0.0001  | 15%        | \$0.000015        |
| **TOTAL**                 |             |           |            | **~\$0.0003/msg** |

**Economia vs pipeline 4 agentes:** -66% (\$0.0009 → \$0.0003)

---

## Configuração e Deploy

### Variáveis de Ambiente

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-2024-08-06
OPENAI_MINI_MODEL=gpt-4o-mini-2024-07-18

# WhatsApp
WHATSAPP_VERIFY_TOKEN=pyloto_webhook_secret
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_ACCESS_TOKEN=EAAx...
WHATSAPP_BUSINESS_ACCOUNT_ID=987654321

# Firestore
FIRESTORE_PROJECT_ID=pyloto-prod
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Redis (cache)
REDIS_URL=redis://localhost:6379

# Ambiente
ENVIRONMENT=production  # ou staging
LOG_LEVEL=INFO
```

### Deploy Google Cloud Run

```bash
# Build
docker build -t gcr.io/pyloto-prod/atende-pyloto:otto-v1 .

# Push
docker push gcr.io/pyloto-prod/atende-pyloto:otto-v1

# Deploy
gcloud run deploy atende-pyloto \
  --image gcr.io/pyloto-prod/atende-pyloto:otto-v1 \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 10 \
  --memory 512Mi \
  --timeout 30s \
  --set-env-vars ENVIRONMENT=production
```

## Limitações Conhecidas

### Processamento async sem fila durável

Atualmente o processamento inbound em modo `async` roda em tasks locais do processo, sem
persistência externa.

**Riscos conhecidos:**

- perda de task em crash/restart abrupto
- processamento interrompido em desligamento forçado

**Mitigações atuais:**

- limite de concorrência (`Semaphore`) para evitar exaustão
- tracking de tasks ativas com drain no shutdown (até 30s)
- dedupe com estado `processing` + rollback em falha para permitir retry seguro
- modo `inline` propaga erro crítico e retorna `500` para acionar retry do provedor

**Evolução recomendada:**

- migrar despacho inbound para fila durável (Cloud Tasks / PubSub / Redis Streams)
- adicionar política explícita de retry/backoff por tipo de falha

---

## Testes

### Estrutura de Testes

```tree
tests/
├── test_ai/                    # Testes dos agentes
│   ├── test_otto_agent.py
│   ├── test_extraction_agent.py
│   ├── test_transcription_agent.py
│   ├── test_context_injector.py
│   └── test_decision_validator.py
├── test_app/                   # Testes de use cases
│   └── use_cases/
│       └── whatsapp/
│           └── test_process_inbound_canonical.py
└── test_e2e/                   # Testes end-to-end (opcional)
    └── test_otto_conversation_flow.py
```

### Executar Testes

```bash
# Todos os testes
pytest tests/ -v

# Apenas testes de IA
pytest tests/test_ai/ -v

# Com cobertura
pytest tests/ --cov=src --cov-report=term --cov-report=html

# E2E (staging apenas)
pytest tests/test_e2e/ -v -m staging
```

**Meta de cobertura:** >= 80% nos arquivos novos (Otto architecture)

---

## Próximos Passos

### ✅ FASE 1: Core (Implementar primeiro - Dias 1-7)

- [ ] Remover pipeline de 4 agentes antigo
- [ ] Implementar ExtractionAgent com structured outputs
- [ ] Implementar TranscriptionAgent (Whisper API)
- [ ] Criar contextos por vertente Pyloto (6 verticais)
- [ ] Implementar ContextInjector
- [ ] Implementar OttoAgent (agente único)
- [ ] Implementar DecisionValidator (3-gate)
- [ ] Expandir LeadContact model
- [ ] Reescrever ProcessInboundCanonicalUseCase
- [ ] Atualizar bootstrap/wiring
- [ ] Testes unitários (>=80% cobertura)

### 🎯 FASE 2: Qualidade (Dias 8-14)

- [ ] Implementar ResponseQualityAgent (auto-QA)
- [ ] Implementar IntentClarificationAgent (desambiguação)
- [ ] Otimizar cache Redis para LeadContact
- [ ] Adicionar typing indicator WhatsApp
- [ ] Deploy staging + validação 48h

### 🚀 FASE 3: Growth (Semanas 3-4)

- [ ] Implementar ConversationSummaryAgent (conversas longas)
- [ ] Implementar HandoffPreparationAgent (briefing humano)
- [ ] Implementar FollowUpSchedulerAgent (proatividade)
- [ ] Dashboard de métricas (BigQuery)
- [ ] Deploy produção gradual (10% → 50% → 100%)

---

## Regras e Padrões

Consulte [`REGRAS_E_PADROES.md`](./REGRAS_E_PADROES.md) para:

- § 1-3: Princípios fundamentais (clareza, SRP, separação de concerns)
- § 4: Tamanho de arquivos (≤200 linhas)
- § 5: Convenções de código (PT-BR, snake_case, type hints)
- § 6: Logging estruturado (sem PII)
- § 7: Structured outputs (Pydantic)
- § 9: Quality gates (ruff, pytest)

---

## Licença

Proprietário - Pyloto Corp © 2026

---

## Contato

- **Fundador:** Jamison Fortes
- **Email:** contato@pyloto.com.br
- **Repositório:** (privado)

---

**Última atualização:** 05 de fevereiro de 2026
**Versão:** 2.0.0-alpha (Otto architecture)
