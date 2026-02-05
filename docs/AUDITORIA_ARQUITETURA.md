# AUDITORIA ARQUITETURAL — Atende_Pyloto

**Data:** 02 de fevereiro de 2026  
**Versão:** 3.0 (LEGADO — pipeline 4 agentes)  
**Escopo:** Conformidade com REGRAS_E_PADROES.md, FUNCIONAMENTO.md e README.md  
**Nota rápida (05/fev/2026):** Pipeline de 4/5 agentes foi removido e substituído pela arquitetura Otto (agente único + utilitários). Este documento permanece como histórico; consulte README.md para o desenho atual.

---

## Resumo Executivo

O repositório **Atende_Pyloto** opera agora na **arquitetura Otto (agente único + utilitários)**. As referências ao pipeline de 4 agentes abaixo são históricas e não refletem o estado atual do código.

### Métricas Atuais

| Métrica               | Valor         | Status |
| --------------------- | ------------- | ------ |
| Arquivos Python       | 261           | —      |
| Linhas totais         | ~12.603       | —      |
| Arquivos > 200 linhas | 0             | ✅     |
| Testes                | 395           | ✅     |
| Arquivos de teste     | 29            | ✅     |
| Linhas de teste       | ~5.593        | —      |
| Gates (ruff)          | ✅ Pass       | ✅     |
| Gates (pytest)        | ✅ 395 passed | ✅     |
| Cobertura geral       | 55%           | ⚠️     |

### Situação Geral

- ✅ **Estrutura de pastas:** CONFORME (ai/, api/, app/, config/, fsm/, utils/)
- ✅ **Boundaries ai/↔app/infra:** CORRIGIDO (OpenAIClient em app/infra/ai/)
- ✅ **Boundaries app↔api:** CORRIGIDO (criptografia em app/infra/crypto)
- ✅ **Use cases:** IMPLEMENTADOS (3 use cases)
- ✅ **Protocolos:** IMPLEMENTADOS (10 interfaces, 356 linhas)
- ✅ **Logging centralizado:** IMPLEMENTADO (config/logging/, 305 linhas)
- ✅ **Observability:** IMPLEMENTADO (app/observability/, 87 linhas)
- ✅ **Arquivos ≤ 200 linhas:** CONFORME (todos arquivos refatorados)
- ✅ **FSM:** IMPLEMENTADO — 97% cobertura, 864 linhas, 11 arquivos
- ✅ **AI (Otto):** IMPLEMENTADO — agente único com utilitários paralelos
- 🗑️ **Pipeline 4-Agentes:** REMOVIDO (substituído por Otto em 05/fev/2026)
- 🗑️ **MasterDecider:** REMOVIDO (governança agora no Otto + validator)
- ⚠️ **Cobertura geral de testes:** 55% (meta: 80%)

---

## 1) Achados por Severidade

### 1.1 ✅ RESOLVIDO — Use Cases Implementados

**Regra:** FUNCIONAMENTO.md § 4.4 — "Use case produz um OutboundCommand"

**Situação atual:** Use cases implementados em `src/app/use_cases/whatsapp/`:

| Arquivo                                                                                 | Linhas | Descrição                 |
| --------------------------------------------------------------------------------------- | ------ | ------------------------- |
| [process_inbound_event.py](src/app/use_cases/whatsapp/process_inbound_event.py)         | 98     | Pipeline inbound (legado) |
| [process_inbound_canonical.py](src/app/use_cases/whatsapp/process_inbound_canonical.py) | 198    | Fluxo canônico completo   |
| [\_inbound_helpers.py](src/app/use_cases/whatsapp/_inbound_helpers.py)                  | 115    | Helpers internos          |
| [send_outbound_message.py](src/app/use_cases/whatsapp/send_outbound_message.py)         | 63     | Envio outbound            |
| [\_\_init\_\_.py](src/app/use_cases/whatsapp/__init__.py)                               | 19     | Exports                   |

**Evidência:** `ProcessInboundCanonicalUseCase` implementa o fluxo canônico de 9 passos.

---

### 1.2 ✅ RESOLVIDO — Protocolos Implementados

**Regra:** REGRAS_E_PADROES.md § 2.3 — `app/protocols/` contém interfaces

**Situação atual:** 9 protocolos em `src/app/protocols/`:

| Arquivo                 | Linhas | Responsabilidade            |
| ----------------------- | ------ | --------------------------- |
| models.py               | 127    | Modelos compartilhados      |
| session_store.py        | 38     | Contrato de store de sessão |
| dedupe.py               | 30     | Contrato de dedupe          |
| http_client.py          | 19     | Contrato HTTP               |
| validator.py            | 17     | Contrato de validação       |
| outbound_sender.py      | 17     | Contrato de envio           |
| decision_audit_store.py | 14     | Contrato de auditoria       |
| payload_builder.py      | 13     | Contrato de builder         |
| normalizer.py           | 13     | Contrato de normalização    |

---

### 1.3 ✅ RESOLVIDO — Logging Centralizado

**Regra:** README.md § 2.4 — `config/logging/` contém config de logging

**Situação atual:** Logging estruturado implementado em `src/config/logging/`:

| Arquivo         | Linhas | Responsabilidade                                        |
| --------------- | ------ | ------------------------------------------------------- |
| config.py       | 139    | `configure_logging()`, `get_logger()`, `log_fallback()` |
| filters.py      | 63     | `CorrelationIdFilter`                                   |
| formatters.py   | 58     | `JsonFormatter`                                         |
| \_\_init\_\_.py | 45     | Exports                                                 |

**Evidência:** `initialize_app()` em `app/bootstrap/` chama `configure_logging()` com `correlation_id_getter`.

---

### 1.4 ✅ RESOLVIDO — Observability Implementado

**Regra:** README.md § 2.3 — `app/observability/` contém logs estruturados, tracing

**Situação atual:** Observability implementado em `src/app/observability/`:

| Arquivo         | Linhas | Responsabilidade               |
| --------------- | ------ | ------------------------------ |
| correlation.py  | 66     | ContextVar para correlation_id |
| \_\_init\_\_.py | 21     | Exports                        |

**Evidência:** `get_correlation_id()`, `set_correlation_id()`, `reset_correlation_id()` funcionando.

---

### 1.5 ✅ RESOLVIDO — Bootstrap Centralizado

**Regra:** REGRAS_E_PADROES.md § 3 — `app/bootstrap` é único lugar para wiring

**Situação atual:** Bootstrap implementado em `src/app/bootstrap/`:

| Arquivo              | Linhas | Responsabilidade                            |
| -------------------- | ------ | ------------------------------------------- |
| \_\_init\_\_.py      | 54     | `initialize_app()`, `initialize_test_app()` |
| whatsapp_adapters.py | 102    | Adapters concretos WhatsApp                 |
| whatsapp_factory.py  | —      | Factory de componentes                      |

**Evidência:** Wiring `app↔api` concentrado corretamente em bootstrap.

---

### 1.6 ✅ RESOLVIDO — Boundary app/coordinators → api/connectors

**Regra:** REGRAS_E_PADROES.md § 3 — `app/` não importa `api/` (exceto bootstrap)

**Situação anterior:** Violação em `sender.py` importando de `api/connectors/whatsapp/flows`.

**Correção aplicada:** Lógica de criptografia movida para `app/infra/crypto/`:

```tree
src/app/infra/crypto/
├── __init__.py (27 linhas) — exports
├── constants.py (8 linhas) — AES_KEY_SIZE, IV_SIZE, TAG_SIZE
├── errors.py (11 linhas) — FlowCryptoError
├── keys.py (76 linhas) — load_private_key, decrypt_aes_key
├── payload.py (80 linhas) — decrypt_flow_data, encrypt_flow_response
└── signature.py (24 linhas) — validate_flow_signature
```

**Resultado:** `sender.py` agora importa de `app.infra.crypto` (boundary correta).

**Compatibilidade:** `api/connectors/whatsapp/flows/` re-exporta de `app/infra/crypto/` para código legado.

---

### 1.7 ✅ RESOLVIDO — Arquivos ≤ 200 Linhas

**Regra:** REGRAS_E_PADROES.md § 4 — "Arquivos ≤ 200 linhas"

**Situação atual:** Todos os arquivos respeitam o limite após refatoração.

**Refatorações realizadas:**

| Arquivo Original  | Antes | Depois | Helper Criado                          |
| ----------------- | ----- | ------ | -------------------------------------- |
| `orchestrator.py` | 262   | 181    | `_orchestrator_helpers.py` (83 linhas) |
| `parser.py`       | 203   | 151    | `_json_extractor.py` (63 linhas)       |
| `extractor.py`    | 207   | 128    | `_extraction_helpers.py` (98 linhas)   |

**Cobertura mantida:** 96% no módulo AI (128 testes passando).

**Impacto:** RESOLVIDO — Nenhum arquivo viola a regra § 4.

---

### 1.8 ✅ CONFIRMADO — Imports TYPE_CHECKING em api/normalizers

**Situação:** Normalizers de canais futuros importam `NormalizedMessage` de `app/protocols`:

```python
if TYPE_CHECKING:
    from app.protocols.models import NormalizedMessage
```

**Análise realizada:**

- 12 normalizers de canais futuros usam TYPE_CHECKING corretamente
- Import acontece apenas para type hints (não runtime)
- Boundary não é violada em produção
- WhatsApp usa import direto de `NormalizedWhatsAppMessage` (modelo próprio em api/)

**Decisão:** ADEQUADO — Padrão correto para canais futuros. Nenhuma alteração necessária.

---

### 1.9 ⚠️ EM PROGRESSO — Cobertura de Testes

**Regra:** REGRAS_E_PADROES.md § 9 — `pytest --cov=src --cov-fail-under=80`

**Situação atual:**

| Métrica           | Esperado | Anterior | Atual |
| ----------------- | -------- | -------- | ----- |
| Testes            | ≥ 50     | 336      | 395   |
| Arquivos de teste | —        | 22       | 29    |
| Cobertura geral   | ≥ 80%    | 52%      | 55%   |

**Cobertura por módulo:**

| Módulo                  | Testes | Cobertura | Status |
| ----------------------- | ------ | --------- | ------ |
| `src/fsm/`              | 23     | 97%       | ✅     |
| `src/ai/`               | 196    | 95%       | ✅     |
| `api/validators/`       | ~40    | ~80%      | ✅     |
| `api/payload_builders/` | ~50    | ~80%      | ✅     |
| `config/logging/`       | 20     | ~70%      | ⚠️     |
| `app/use_cases/`        | 18     | ~60%      | ⚠️     |
| `config/settings/`      | 0      | 0%        | ❌     |
| `app/coordinators/`     | 0      | 0%        | ❌     |

**Testes existentes (29 arquivos):**

```tree
tests/
├── api/
│   ├── connectors/whatsapp/webhook/test_verify.py
│   ├── connectors/whatsapp/webhook/test_receive.py
│   ├── connectors/whatsapp/inbound/test_event_id.py
│   ├── payload_builders/test_whatsapp_builders.py
│   └── validators/test_whatsapp_validators.py
├── app/
│   ├── use_cases/whatsapp/test_process_inbound_event.py
│   ├── use_cases/whatsapp/test_send_outbound_message.py
│   └── services/test_master_decider.py
├── test_config/test_logging.py
├── test_fsm/test_fsm_complete.py
└── test_ai/ (11 arquivos, ~2.000 linhas total)
    ├── test_models.py
    ├── test_models_decision_agent.py
    ├── test_models_state_agent.py
    ├── test_orchestrator.py
    ├── test_prompts.py
    ├── test_agent_prompts.py
    ├── test_parser.py
    ├── test_utils_agent_parser.py
    ├── test_config_agent_config.py
    ├── test_ai_pipeline.py
    └── conftest.py
```

**Falta cobertura prioritária:**

1. ❌ `config/settings/` — 0% (50+ arquivos de settings)
2. ❌ `app/coordinators/` — 0% (fluxos inbound/outbound)
3. ⚠️ `app/bootstrap/` — parcial (wiring e factories)

---

### 1.10 ✅ IMPLEMENTADO — FSM Completa

**Regra:** FUNCIONAMENTO.md § 4.4 — "FSM avalia estado atual e transições possíveis"

**Situação atual:** FSM **IMPLEMENTADA** com 97% de cobertura de testes.

```tree
src/fsm/                           (864 linhas total, 11 arquivos)
├── __init__.py                    (76 linhas — exports)
├── states/
│   ├── __init__.py                (21 linhas)
│   └── session.py                 (89 linhas — SessionState enum)
├── transitions/
│   ├── __init__.py                (21 linhas)
│   └── rules.py                   (135 linhas — VALID_TRANSITIONS)
├── types/
│   ├── __init__.py                (12 linhas)
│   └── transition.py              (98 linhas — StateTransition dataclass)
├── rules/
│   ├── __init__.py                (25 linhas)
│   └── guards.py                  (176 linhas — guards de transição)
└── manager/
    ├── __init__.py                (17 linhas)
    └── machine.py                 (194 linhas — FSMStateMachine class)
```

**Componentes implementados:**

- ✅ `SessionState` enum (10 estados canônicos)
- ✅ `VALID_TRANSITIONS` dict com transições explícitas
- ✅ `StateTransition` dataclass com histórico
- ✅ `FSMStateMachine` class com validação
- ✅ Guards de transição (anti-loop, terminais)
- ✅ 23 testes específicos para FSM

**Cobertura de testes:** 97% (23 testes)

**Referência:** Documentação completa na Seção 9.

**Próximo passo:** Integrar FSMStateMachine em `ProcessInboundEventUseCase`

**Impacto:** RESOLVIDO — FSM implementada conforme Seção 9.

---

### 1.11 ✅ IMPLEMENTADO — Pipeline de 4 Agentes LLM

**Regra:** FUNCIONAMENTO.md § 4.4 — "IA (quando aplicável)"
**Regra:** README.md § 3 — "Pipeline de 4 agentes LLM"

**Situação atual:** Pipeline de 4 agentes **IMPLEMENTADO** com 95% de cobertura de testes.

```pipeline
ProcessInboundCanonicalUseCase
        │
        ▼
   AIOrchestrator (coordena 4 agentes)
        │
        ├─────────────┬─────────────┐
        ▼             ▼             ▼
  StateAgent    ResponseAgent  MessageTypeAgent
   (LLM #1)       (LLM #2)       (LLM #3)
        │             │             │
        └─────────────┴─────────────┘
                      │ (paralelo via asyncio.gather)
                      ▼
              DecisionAgent (LLM #4)
                      │
                      ▼
              MasterDecision
```

**Arquitetura do módulo AI:**

```tree módulo AI
src/ai/                          (2.819 linhas total, 23 arquivos)
├── __init__.py                  (79 linhas - exports públicos)
├── config/
│   ├── __init__.py              (re-exports)
│   ├── settings.py              (87 linhas - AISettings)
│   └── agent_config.py          (81 linhas - YAML loader com cache)
├── core/
│   ├── __init__.py              (re-exports)
│   └── client.py                (113 linhas - AIClientProtocol)
├── models/
│   ├── __init__.py              (re-exports)
│   ├── state_agent.py           (91 linhas - LLM #1: StateAgent)
│   ├── response_generation.py   (130 linhas - LLM #2: ResponseAgent)
│   ├── message_type_selection.py (60 linhas - LLM #3: MessageTypeAgent)
│   ├── decision_agent.py        (75 linhas - LLM #4: DecisionAgent)
│   └── event_detection.py       (53 linhas - legado)
├── prompts/
│   ├── __init__.py              (re-exports)
│   ├── base_prompts.py          (170 linhas)
│   ├── state_agent_prompt.py    (61 linhas - prompt LLM #1)
│   ├── response_agent_prompt.py (59 linhas - prompt LLM #2)
│   ├── message_type_agent_prompt.py (54 linhas - prompt LLM #3)
│   ├── decision_agent_prompt.py (68 linhas - prompt LLM #4)
│   ├── state_prompts.py         (131 linhas)
│   └── validation_prompts.py    (150 linhas)
├── rules/
│   ├── __init__.py              (re-exports)
│   └── fallbacks.py             (145 linhas - fallbacks determinísticos)
├── services/
│   ├── __init__.py              (re-exports)
│   ├── orchestrator.py          (173 linhas - AIOrchestrator 4 agentes)
│   └── _orchestrator_helpers.py (83 linhas - helpers)
└── utils/
    ├── __init__.py              (re-exports)
    ├── parser.py                (151 linhas - JSON parsing)
    ├── agent_parser.py          (137 linhas - parsers 4 agentes)
    ├── sanitizer.py             (105 linhas - PII masking)
    └── _json_extractor.py       (63 linhas - extração JSON)
```

**Especificações do pipeline:**

| Item                   | Valor                                        |
| ---------------------- | -------------------------------------------- |
| Paralelização          | Agentes 1, 2, 3 em paralelo (asyncio.gather) |
| Threshold de confiança | 0.7                                          |
| Fallback               | "Desculpe, não entendi. Pode reformular?"    |
| Escalação para humano  | Após 3x consecutivas com confidence < 0.7    |
| Candidatos de resposta | 3 (formal, casual, empático)                 |
| Tipos de mensagem      | text, interactive_button, interactive_list   |
| Estados FSM            | 10 fixos (SessionState enum)                 |
| Config dos agentes     | config/agents/{agent_name}.yaml              |

**Cobertura de testes:** 95% (196 testes específicos para AI)

**Componentes implementados:**

- ✅ `AIClientProtocol` com métodos para 4 agentes
- ✅ `StateAgentResult` (LLM #1) — sugere próximos estados
- ✅ `ResponseGenerationResult` (LLM #2) — gera 3 candidatos
- ✅ `MessageTypeSelectionResult` (LLM #3) — seleciona tipo
- ✅ `DecisionAgentResult` (LLM #4) — consolida e decide
- ✅ `OrchestratorResult` — resultado consolidado
- ✅ Fallbacks determinísticos (REGRAS_E_PADROES.md § 7)
- ✅ Sanitização de PII (REGRAS_E_PADROES.md § 6)
- ✅ YAML config com cache para agentes

**Impacto:** RESOLVIDO — AI 4-agentes implementada conforme README.md.

---

### 1.12 ✅ RESOLVIDO — app/services/whatsapp Removido

**Situação anterior:** `app/services/whatsapp/` misturava responsabilidades.

**Situação atual:** Pasta removida. Lógica movida para:

- Use cases em `app/use_cases/whatsapp/`
- Adapters em `app/bootstrap/whatsapp_adapters.py`

---

## 2) Sumário de Conformidade por Regra

| Regra                          | Status | Observação                                |
| ------------------------------ | ------ | ----------------------------------------- |
| § 1.1 Clareza > esperteza      | ✅     | Código legível                            |
| § 1.2 SRP real                 | ✅     | Módulos pequenos e focados                |
| § 1.3 Determinismo             | ✅     | Sem estado global problemático            |
| § 1.4 Boundaries               | ✅     | Criptografia movida para app/infra/crypto |
| § 1.5 Defesa em profundidade   | ✅     | Validações presentes                      |
| § 2 Estrutura de pastas        | ✅     | Todas as pastas conforme README           |
| § 3 Separação de camadas       | ✅     | app/infra/crypto respeita boundary        |
| § 4 Limite 200 linhas          | ✅     | Todos arquivos ≤ 200 linhas (refatorado)  |
| § 5 Estilo (PT-BR, snake_case) | ✅     | Conforme                                  |
| § 6 Logs sem PII               | ✅     | Logs estruturados implementados           |
| § 7 Segurança                  | ✅     | Validação de assinatura implementada      |
| § 8 Testes                     | ⚠️     | Cobertura 50% (305 testes, meta 80%)      |
| § 9 Gates                      | ✅     | ruff + pytest passando                    |

---

## 3) Estrutura Atual vs Esperada

### 3.1 config/logging/ ✅ IMPLEMENTADO

**Esperado (README.md § 2.4):**

```tree
config/logging/: logging config
```

**Atual:**

```tree
config/logging/
├── __init__.py (45 linhas) — exports
├── config.py (139 linhas) — configure_logging(), get_logger()
├── filters.py (63 linhas) — CorrelationIdFilter
└── formatters.py (58 linhas) — JsonFormatter
```

### 3.2 config/settings/ ✅ IMPLEMENTADO

**Esperado (README.md § 2.4):**

```tree
config/settings/: settings por canal/provedor
```

**Atual:**

```tree
config/settings/
├── __init__.py (104 linhas) — agregador
├── whatsapp.py (153 linhas) — ✅ implementado
├── instagram.py, facebook.py, ... (stubs)
├── ai/ — OpenAI, LLM phases, flood
├── base/ — core, dedupe, session
└── infra/ — firestore, gcs, pubsub, cloud_tasks
```

### 3.3 app/observability/ ✅ IMPLEMENTADO

**Esperado (README.md § 2.3):**

```tree
app/observability/: logs estruturados, tracing/correlation, métricas
```

**Atual:**

```tree
app/observability/
├── __init__.py (21 linhas) — exports
└── correlation.py (66 linhas) — ContextVar correlation_id
```

### 3.4 app/use_cases/ ✅ IMPLEMENTADO

**Esperado (FUNCIONAMENTO.md § 4):**

```tree
app/use_cases/: casos de uso
```

**Atual:**

```tree
app/use_cases/
├── __init__.py
└── whatsapp/
    ├── __init__.py (19 linhas)
    ├── process_inbound_event.py (98 linhas) ✅
    └── send_outbound_message.py (63 linhas) ✅
```

### 3.5 app/protocols/ ✅ IMPLEMENTADO

**Esperado (README.md § 2.3):**

```tree
app/protocols/: contratos/interfaces
```

**Atual:** 9 protocolos implementados (323 linhas total).

### 3.6 fsm/ ✅ IMPLEMENTADO

**Esperado:**

```tree
fsm/states/: definições dos estados
fsm/transitions/: transições permitidas
fsm/rules/: regras de transição
fsm/manager/: aplicação/validação da FSM
```

**Atual:**

```tree
fsm/                           (864 linhas, 11 arquivos)
├── __init__.py                (76 linhas — exports)
├── states/session.py          (89 linhas — SessionState enum)
├── transitions/rules.py       (135 linhas — VALID_TRANSITIONS)
├── types/transition.py        (98 linhas — StateTransition)
├── rules/guards.py            (176 linhas — guards)
└── manager/machine.py         (194 linhas — FSMStateMachine)
```

**Cobertura:** 97% (23 testes)

### 3.7 ai/ ✅ IMPLEMENTADO

**Esperado:**

```tree
ai/config/, ai/core/, ai/models/, ai/prompts/, ai/rules/, ai/services/, ai/utils/
```

**Atual:**

```tree
ai/                            (1.848 linhas, 21 arquivos)
├── __init__.py                (85 linhas — exports)
├── config/settings.py         (85 linhas — AISettings)
├── core/client.py             (170 linhas — AIClientProtocol, MockAIClient)
├── models/
│   ├── event_detection.py     (52 linhas)
│   ├── response_generation.py (81 linhas)
│   └── message_type_selection.py (55 linhas)
├── prompts/
│   ├── base_prompts.py        (158 linhas)
│   ├── state_prompts.py       (138 linhas)
│   └── validation_prompts.py  (149 linhas)
├── rules/fallbacks.py         (132 linhas)
├── services/orchestrator.py   (262 linhas) ⚠️ > 200
└── utils/
    ├── parser.py              (203 linhas) ⚠️ > 200
    └── sanitizer.py           (115 linhas)
```

**Cobertura:** 95% (128 testes)

---

## 4) Checklist de Validação

| Item                                           | Status                                      |
| ---------------------------------------------- | ------------------------------------------- |
| ✅ `app/` não importa `api/` fora de bootstrap | ✅ (criptografia movida para app/infra/)    |
| ✅ `api/` não importa `app/` em runtime        | ✅ (TYPE_CHECKING + re-exports para legado) |
| ✅ Arquivos ≤ 200 linhas                       | ✅ Todos conforme (refatorado)              |
| ✅ `app/use_cases/` ≥ 2 casos de uso           | ✅                                          |
| ✅ `app/protocols/` ≥ 5 interfaces             | ✅ 9 interfaces                             |
| ✅ `config/logging/` implementado              | ✅                                          |
| ✅ `app/observability/` implementado           | ✅                                          |
| ✅ `app/infra/crypto/` implementado            | ✅                                          |
| ✅ `ruff check src/` passa                     | ✅                                          |
| ✅ `pytest` passa                              | ✅ 305 passed                               |
| ⚠️ `pytest --cov-fail-under=80`                | ⚠️ 50% (meta: 80%)                          |
| ✅ FSM implementada                            | ✅ 97% cobertura                            |
| ✅ AI implementada                             | ✅ 96% cobertura                            |

---

## 5) Recomendações Priorizadas

### FASE 1: CRÍTICO (Bloqueia produção)

#### 5.1 ✅ CONCLUÍDO — extractor.py Refatorado

**Arquivo:** `src/api/normalizers/whatsapp/extractor.py`

**Ação realizada:** Helpers extraídos para `_extraction_helpers.py` (207→128 linhas).

---

#### 5.2 ⚠️ EM PROGRESSO — Testes

**Meta:** ≥ 80% cobertura geral.

**Concluído:**

1. ✅ `src/fsm/` — 97% cobertura (23 testes)
2. ✅ `src/ai/` — 95% cobertura (128 testes)
3. ✅ `api/validators/whatsapp/` — ~80% (testes)
4. ✅ `api/payload_builders/whatsapp/` — ~80% (testes)
5. ✅ `config/logging/` — ~70% cobertura (20 testes)
6. ✅ `app/use_cases/whatsapp/` — ~60% (18 testes)

**Próximos:**

1. `config/settings/` — 0% (50+ arquivos)
2. `app/coordinators/` — 0% (fluxos críticos)
3. `app/bootstrap/` — parcial

---

#### 5.3 ⚠️ NOVO — Refatorar Arquivos > 200 Linhas

**Arquivos a refatorar:**

| Arquivo                       | Linhas | Ação Recomendada                |
| ----------------------------- | ------ | ------------------------------- |
| `ai/services/orchestrator.py` | 262    | Extrair sanitização e validação |
| `ai/utils/parser.py`          | 203    | Mover fallbacks ou extract_json |

**Impacto:** MÉDIO — Código funcional mas viola regra §4.

---

### FASE 3: MÉDIO (Qualidade)

#### 5.5 ✅ CONCLUÍDO — Boundary em flows/sender.py Resolvida

**Ação realizada:** Lógica de criptografia movida para `app/infra/crypto/`.

**Arquivos criados:**

- `app/infra/crypto/__init__.py` (27 linhas)
- `app/infra/crypto/constants.py` (8 linhas)
- `app/infra/crypto/errors.py` (11 linhas)
- `app/infra/crypto/keys.py` (76 linhas)
- `app/infra/crypto/payload.py` (80 linhas)
- `app/infra/crypto/signature.py` (24 linhas)

**Resultado:** `sender.py` agora importa de `app.infra.crypto` (boundary correta).

---

## 6) Gates Atuais

```bash
# ✅ PASSANDO
ruff check src/
pytest -q

# ❌ FALHANDO (cobertura insuficiente)
pytest --cov=src --cov-fail-under=80
```

---

## 7) Evolução desde Última Auditoria

| Item                  | v1.0    | v2.0   | v2.1   | v2.2   | v2.3   | v2.5    | v2.6    | Delta |
| --------------------- | ------- | ------ | ------ | ------ | ------ | ------- | ------- | ----- |
| Arquivos Python       | 146     | 219    | 220    | 226    | 226    | 241     | 243     | +2    |
| Linhas totais         | ~5.000  | ~7.000 | ~7.200 | ~8.000 | ~8.500 | ~10.000 | ~10.460 | +460  |
| Use cases             | 0       | 2      | 2      | 2      | 2      | 2       | 2       | —     |
| Protocolos            | 0       | 9      | 9      | 9      | 9      | 9       | 9       | —     |
| Logging centralizado  | ❌      | ✅     | ✅     | ✅     | ✅     | ✅      | ✅      | —     |
| Observability         | ❌      | ✅     | ✅     | ✅     | ✅     | ✅      | ✅      | —     |
| Bootstrap             | Parcial | ✅     | ✅     | ✅     | ✅     | ✅      | ✅      | —     |
| Boundaries            | ❌      | ⚠️     | ⚠️     | ✅     | ✅     | ✅      | ✅      | —     |
| Arquivos > 200 linhas | 1       | 1      | 0      | 0      | 0      | 2       | 0       | ✅    |
| Testes                | 3       | 8      | 26     | 26     | 26     | 305     | 305     | —     |
| Cobertura             | ~2%     | ~3%    | ~12%   | ~12%   | ~12%   | 50%     | 50%     | —     |
| FSM implementada      | ❌      | ❌     | ❌     | ❌     | ⚠️     | ✅      | ✅      | —     |
| AI implementada       | ❌      | ❌     | ❌     | ❌     | ⚠️     | ✅      | ✅      | —     |

---

## 8) Próximos Passos

### Prioridade 1: ALTO (antes: CRÍTICO - refatoração concluída)

1. ✅ **Refatorar arquivos > 200 linhas:** _(Concluído em v2.7)_
   - `ai/services/orchestrator.py` (262 → 181) ✅
   - `ai/utils/parser.py` (203 → 151) ✅
   - Helpers extraídos: `_orchestrator_helpers.py` (83 linhas), `_json_extractor.py` (63 linhas)

### Prioridade 2: ALTO

2.⚠️ **Aumentar cobertura de testes** (50% → 80%):
    - `config/settings/` — 0% (muitos stubs)
    - `app/coordinators/` — 0% (fluxos críticos)
    - `app/bootstrap/` — parcial

### Prioridade 3: MÉDIO

3.✅ **Integrar FSM em `ProcessInboundEventUseCase`**
4.✅ **Integrar AIOrchestrator em `ProcessInboundEventUseCase`**
5.⚠️ **Implementar OpenAIClient real** (substituir MockAIClient em produção)

### Concluídos

- ~~Corrigir extractor.py (≤ 200 linhas)~~ ✅
- ~~Adicionar testes para use cases~~ ✅ (18 testes)
- ~~Resolver boundary em flows/sender.py~~ ✅
- ~~Documentar FSM de referência~~ ✅ (Seção 9)
- ~~Implementar FSM~~ ✅ (97% cobertura)
- ~~Documentar AI de referência~~ ✅ (Seção 10)
- ~~Implementar AI~~ ✅ (95% cobertura)

---

---

## 9) Análise FSM — Referência de pyloto_corp

Esta seção documenta a FSM existente em `pyloto_corp` como referência para implementação controlada em `Atende_Pyloto`.

### 9.1 Estrutura Encontrada em pyloto_corp

```tree
pyloto_corp/src/pyloto_corp/domain/
├── fsm/
│   ├── initial_state.py          — estado inicial canônico
│   └── state_mapping.py          — mapeamento FSM → LLM-facing
├── fsm_states.py                  — ConversationState, FSMStateMachine, StateTransition
└── session/
    └── states.py                  — SessionState (10 estados canônicos)
```

### 9.2 Componentes Identificados

#### 9.2.1 Estados Internos (`ConversationState` — 11 estados)

| Estado                   | Descrição                     | Terminal? |
| ------------------------ | ----------------------------- | --------- |
| `INIT`                   | Inicial, pré-identificação    | ❌        |
| `IDENTIFYING`            | Identificando usuário         | ❌        |
| `UNDERSTANDING_INTENT`   | Classificando intenção        | ❌        |
| `PROCESSING`             | Processando requisição        | ❌        |
| `GENERATING_RESPONSE`    | Gerando resposta              | ❌        |
| `SELECTING_MESSAGE_TYPE` | Selecionando tipo de mensagem | ❌        |
| `AWAITING_USER`          | Aguardando input do usuário   | ❌        |
| `ESCALATING`             | Escalando para humano         | ❌        |
| `COMPLETED`              | **Concluído com sucesso**     | ✅        |
| `FAILED`                 | **Falha irrecuperável**       | ✅        |
| `SPAM`                   | **Detectado como spam**       | ✅        |

#### 9.2.2 Estados LLM-Facing (`SessionState` — 10 estados)

| Estado                | Descrição                    | Terminal? |
| --------------------- | ---------------------------- | --------- |
| `INITIAL`             | Sessão iniciada              | ❌        |
| `TRIAGE`              | Classificação em andamento   | ❌        |
| `COLLECTING_INFO`     | Coleta estruturada           | ❌        |
| `GENERATING_RESPONSE` | Preparando resposta          | ❌        |
| `HANDOFF_HUMAN`       | **Encaminhado para humano**  | ✅        |
| `SELF_SERVE_INFO`     | **Atendido com informação**  | ✅        |
| `ROUTE_EXTERNAL`      | **Encaminhado externamente** | ✅        |
| `SCHEDULED_FOLLOWUP`  | **Follow-up agendado**       | ✅        |
| `TIMEOUT`             | **Expirou por inatividade**  | ✅        |
| `ERROR`               | **Falha interna**            | ✅        |

#### 9.2.3 Classe FSMStateMachine

```python
@dataclass
class StateTransition:
    from_state: ConversationState
    to_state: ConversationState
    trigger: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 1.0

class FSMStateMachine:
    INITIAL_STATES = {ConversationState.INIT}
    TERMINAL_STATES = {COMPLETED, FAILED, SPAM}

    VALID_TRANSITIONS = {
        INIT: {IDENTIFYING, SPAM},
        IDENTIFYING: {UNDERSTANDING_INTENT, SPAM},
        UNDERSTANDING_INTENT: {PROCESSING, ESCALATING},
        # ... transições explícitas
    }

    def can_transition_to(self, target) -> bool
    def transition(self, target, trigger, metadata, confidence) -> bool
    def get_history(self) -> list[StateTransition]
    def get_state_summary(self) -> dict
    def reset(self) -> None
```

#### 9.2.4 Mapeamento FSM → LLM (state_mapping.py)

Converte estado interno para estado exposto à LLM:

```python
_FSM_TO_LLM_MAP = {
    FSM.INIT: LLM.INIT,
    FSM.IDENTIFYING: LLM.INIT,           # Estados internos → INIT
    FSM.AWAITING_USER: LLM.AWAITING_USER,
    FSM.ESCALATING: LLM.HANDOFF_HUMAN,
    FSM.COMPLETED: LLM.SELF_SERVE_INFO,
    FSM.FAILED: LLM.FAILED_INTERNAL,
    FSM.SPAM: LLM.DUPLICATE_OR_SPAM,
}
```

### 9.3 Pontos Fortes (a Preservar)

1. **Separação clara** entre estados internos (FSM) e estados expostos (LLM)
2. **Transições explícitas** via `VALID_TRANSITIONS` dict
3. **Histórico rastreável** via `StateTransition` dataclass
4. **Confidence score** em transições (útil para LLM decisions)
5. **Imutabilidade de terminais** — estados terminais não permitem saída
6. **Logging estruturado** em cada transição (sem PII)
7. **Testes existentes** cobrindo cenários válidos e inválidos

### 9.4 Fragilidades Identificadas

| Severidade | Achado                                                                               | Impacto                |
| ---------- | ------------------------------------------------------------------------------------ | ---------------------- |
| **Médio**  | Dois enums separados (`ConversationState` + `SessionState`) sem sincronização formal | Risco de drift         |
| **Médio**  | `initial_state.py` faz import circular com `state_mapping.py`                        | Acoplamento            |
| **Baixo**  | `metadata: dict[str, Any]` não tipado                                                | Perda de type safety   |
| **Baixo**  | Sem validação de `trigger` (string livre)                                            | Inconsistência em logs |

### 9.5 Recomendações para Atende_Pyloto

#### Prioridade 1: Estados e Transições

1. **Usar apenas `SessionState`** (10 estados) como enum canônico
2. **Não criar `ConversationState` separado** — evitar duplicação
3. **Transições em dict tipado** seguindo padrão de `pyloto_corp`

#### Prioridade 2: Implementação Mínima

```tree
src/fsm/
├── __init__.py           — exports
├── states/
│   ├── __init__.py
│   └── session.py        — SessionState enum + TERMINAL_STATES
├── transitions/
│   ├── __init__.py
│   └── rules.py          — VALID_TRANSITIONS dict
├── manager/
│   ├── __init__.py
│   └── machine.py        — FSMStateMachine class
└── types/
    ├── __init__.py
    └── transition.py     — StateTransition dataclass
```

#### Prioridade 3: Integrações

1. Integrar FSM em `ProcessInboundEventUseCase`
2. Persistir estado via `SessionStoreProtocol`
3. Expor `get_state_summary()` para observability

### 9.6 Próximos Passos FSM

| #   | Ação                                                   | Dependência | Risco |
| --- | ------------------------------------------------------ | ----------- | ----- |
| 1   | Criar `fsm/states/session.py` com SessionState         | —           | Baixo |
| 2   | Criar `fsm/transitions/rules.py` com VALID_TRANSITIONS | #1          | Baixo |
| 3   | Criar `fsm/types/transition.py` com StateTransition    | —           | Baixo |
| 4   | Criar `fsm/manager/machine.py` com FSMStateMachine     | #1, #2, #3  | Médio |
| 5   | Integrar em ProcessInboundEventUseCase                 | #4          | Médio |
| 6   | Adicionar testes para FSM                              | #4          | Baixo |

---

## 10) Análise AI — Referência de pyloto_corp

Esta seção documenta a estrutura de IA existente em `pyloto_corp` como referência para implementação controlada em `Atende_Pyloto`.

### 10.1 Estrutura Encontrada em pyloto_corp

```tree
pyloto_corp/src/pyloto_corp/ai/
├── __init__.py                     — exports (vazio)
├── config/                         — (vazio)
├── contracts/
│   ├── __init__.py                 — re-exports
│   ├── event_detection.py          — EventDetectionRequest/Result
│   ├── message_type_selection.py   — MessageTypeSelectionRequest/Result
│   └── response_generation.py      — ResponseGenerationRequest/Result/Option
├── context_loader.py               — InstitucionalContextLoader (236 linhas)
├── guardrails.py                   — (esqueleto, 4 linhas)
├── knowledge.py                    — (esqueleto, 4 linhas)
├── openai_client.py                — OpenAIClientManager (165 linhas)
├── openai_parser.py                — Parsers + fallbacks (157 linhas)
├── openai_prompts.py               — System prompts + formatters (186 linhas)
├── orchestrator.py                 — LEGACY: IntentClassifier, OutcomeDecider (267 linhas)
├── prompts.py                      — prompts adicionais
├── prompts_institutional.py        — prompts institucionais
├── sanitizer.py                    — Mascaramento PII (99 linhas)
└── assistant_*.py                  — helpers de assistente
```

### 10.2 Componentes Identificados

#### 10.2.1 Contratos Pydantic (3 pontos de LLM)

| Contrato                             | Arquivo                             | Descrição                                              |
| ------------------------------------ | ----------------------------------- | ------------------------------------------------------ |
| `EventDetectionRequest/Result`       | contracts/event_detection.py        | Input/output para LLM #1 (detectar evento e intenção)  |
| `ResponseGenerationRequest/Result`   | contracts/response_generation.py    | Input/output para LLM #2 (gerar resposta)              |
| `MessageTypeSelectionRequest/Result` | contracts/message_type_selection.py | Input/output para LLM #3 (selecionar tipo de mensagem) |

**Campos comuns:**

- `confidence: float` — confiança da resposta (0.0 a 1.0)
- `rationale: str | None` — justificativa para debug
- `requires_followup: bool` / `requires_human_review: bool` — flags de escalação

#### 10.2.2 OpenAI Client Manager

```python
class OpenAIClientManager:
    """Gerenciador do cliente OpenAI com retry e timeout."""

    def __init__(self, api_key: str | None = None):
        self._model = "gpt-4o-mini"
        self._timeout = 15.0
        self._max_retries = 3
        self._client = AsyncOpenAI(...)

    async def detect_event(...) -> EventDetectionResult
    async def generate_response(...) -> ResponseGenerationResult
    async def select_message_type(...) -> MessageTypeSelectionResult
```

**Características:**

- Cliente assíncrono (`AsyncOpenAI`)
- Retry configurável no client (não nas chamadas)
- Timeout global de 15s
- Fallback determinístico em caso de erro (APIConnectionError, APIError, APITimeoutError)

#### 10.2.3 Parser de Respostas + Fallbacks

```python
# openai_parser.py
def parse_event_detection_response(raw_response: str) -> EventDetectionResult
def parse_response_generation_response(raw_response: str) -> ResponseGenerationResult
def parse_message_type_response(raw_response: str) -> MessageTypeSelectionResult

# Fallbacks determinísticos
def _fallback_event_detection() -> EventDetectionResult
def _fallback_response_generation() -> ResponseGenerationResult
def _fallback_message_type_selection() -> MessageTypeSelectionResult

# Helper
def _extract_json_from_response(response: str) -> dict[str, Any]
```

**Tratamento de JSON:**

- Remove markdown code blocks (```json)
- Valida que é dict
- Retorna fallback em caso de erro

#### 10.2.4 System Prompts

| Prompt                                | Função                      | Uso    |
| ------------------------------------- | --------------------------- | ------ |
| `get_event_detection_prompt()`        | Detectar evento e intenção  | LLM #1 |
| `get_response_generation_prompt()`    | Gerar resposta contextual   | LLM #2 |
| `get_message_type_selection_prompt()` | Selecionar tipo de mensagem | LLM #3 |

**Características:**

- Prompts em português (PT-BR)
- Instruções para retornar JSON válido
- Contexto institucional injetado via `get_system_prompt_context()`
- Temperature diferente por etapa (0.2-0.4)

#### 10.2.5 Sanitizador de PII

```python
# sanitizer.py
def sanitize_response_content(text: str) -> str
def mask_pii_in_history(messages: list[str]) -> list[str]

# Patterns regex para:
# - CPF, CNPJ
# - E-mail
# - Telefone BR
```

**Uso:** Aplicar antes de enviar histórico para LLM (minimização de dados).

#### 10.2.6 Context Loader

```python
class InstitucionalContextLoader:
    def load_vertentes() -> str      # docs/institucional/vertentes.md
    def load_visao_principios() -> str
    def load_contexto_llm() -> str
    # Cache interno para evitar re-leitura
```

**Uso:** Carregar documentos institucionais para enriquecer prompts.

### 10.3 Pontos Fortes (a Preservar)

1. **Separação clara** entre contratos (Pydantic), client (async), prompts e parsers
2. **Fallbacks determinísticos** em todas as etapas de LLM
3. **Sanitização de PII** antes de enviar para LLM
4. **Contratos tipados** com Pydantic (validação automática)
5. **Confidence score** em todas as respostas de LLM
6. **Logs estruturados** via `log_fallback()` (sem PII)
7. **Timeout e retry** configuráveis no client

### 10.4 Fragilidades Identificadas

| Severidade | Achado                                                            | Impacto                            |
| ---------- | ----------------------------------------------------------------- | ---------------------------------- |
| **Alto**   | `context_loader.py` tem 236 linhas (> 200)                        | Viola REGRAS_E_PADROES.md § 4      |
| **Alto**   | `orchestrator.py` marcado como LEGACY (267 linhas)                | Código obsoleto, não usar          |
| **Médio**  | Arquivos `guardrails.py` e `knowledge.py` são esqueletos          | Não implementados                  |
| **Médio**  | Dependência de `pyloto_corp.domain.enums` (Intent, Outcome, etc.) | Enums não existem em Atende_Pyloto |
| **Médio**  | `openai_prompts.py` tem 186 linhas                                | Próximo do limite                  |
| **Baixo**  | `_client` como instância global em `get_openai_client()`          | Dificulta testes                   |

### 10.5 Recomendações para Atende_Pyloto

#### Prioridade 1: Estrutura Conforme REGRAS_E_PADROES.md

```tree
src/ai/
├── __init__.py           — exports públicos
├── config/
│   ├── __init__.py
│   └── settings.py       — AISettings (model, timeout, thresholds)
├── contracts/
│   ├── __init__.py       — re-exports
│   ├── event_detection.py
│   ├── response_generation.py
│   └── message_type_selection.py
├── core/
│   ├── __init__.py
│   └── client.py         — AIClientProtocol + OpenAIClient
├── models/
│   ├── __init__.py
│   └── enums.py          — Intent, Outcome (se necessário)
├── prompts/
│   ├── __init__.py
│   ├── base_prompts/
│   │   └── system.py     — get_system_prompt()
│   ├── state_prompts/
│   │   └── event.py      — get_event_detection_prompt()
│   └── validation_prompts/
│       └── guardrails.py — regras de validação
├── rules/
│   ├── __init__.py
│   └── fallbacks.py      — fallback_event_detection(), etc.
├── services/
│   ├── __init__.py
│   └── orchestrator.py   — AIOrchestrator (novo, não LEGACY)
└── utils/
    ├── __init__.py
    ├── parser.py         — parse_llm_response(), extract_json()
    └── sanitizer.py      — sanitize_pii(), mask_history()
```

#### Prioridade 2: Contratos Tipados (dataclasses, não Pydantic)

Conforme padrão do repositório (usa dataclasses, não Pydantic):

```python
@dataclass(frozen=True, slots=True)
class EventDetectionResult:
    event: str
    detected_intent: str
    confidence: float
    requires_followup: bool = False
    rationale: str | None = None
```

#### Prioridade 3: Client com Protocol (DI)

```python
class AIClientProtocol(Protocol):
    async def detect_event(...) -> EventDetectionResult: ...
    async def generate_response(...) -> ResponseGenerationResult: ...
    async def select_message_type(...) -> MessageTypeSelectionResult: ...

class OpenAIClient:  # implementação concreta
    ...
```

#### Prioridade 4: Sem IO Direto

Conforme REGRAS_E_PADROES.md § 2.1:

- `ai/` não faz IO direto
- Context loader recebe documentos via injeção (não lê filesystem)
- HTTP client injetado via protocol

### 10.6 ✅ Implementação Concluída — Fluxo Canônico

Os seguintes módulos foram implementados para o fluxo canônico:

| Módulo                                                | Linhas | Descrição                   |
| ----------------------------------------------------- | ------ | --------------------------- |
| `app/infra/ai/openai_client.py`                       | 156    | Cliente real OpenAI (httpx) |
| `app/infra/ai/_openai_http.py`                        | 99     | Helper HTTP para OpenAI     |
| `app/sessions/models.py`                              | 150    | Session e SessionContext    |
| `app/sessions/manager.py`                             | 103    | Gerenciador de sessões      |
| `app/services/master_decider.py`                      | 121    | Decisor mestre (governança) |
| `app/services/_decider_helpers.py`                    | 116    | Helpers do decisor          |
| `app/use_cases/whatsapp/process_inbound_canonical.py` | 198    | Use case canônico           |
| `app/use_cases/whatsapp/_inbound_helpers.py`          | 124    | Helpers do use case         |

**Nota importante:** `OpenAIClient` foi movido de `ai/core/` para `app/infra/ai/` conforme REGRAS_E_PADROES.md § 2.1 ("ai/ não pode fazer IO direto").

**Testes adicionados:**

| Arquivo de teste                            | Testes | Linhas |
| ------------------------------------------- | ------ | ------ |
| `tests/test_ai/test_openai_client.py`       | 9      | 185    |
| `tests/app/sessions/test_session_models.py` | 13     | 187    |
| `tests/app/services/test_master_decider.py` | 8      | 244    |

---

## 11) Estrutura Atual Detalhada por Módulo

### 11.1 Módulo `ai/` — 22 arquivos, 1.880 linhas

```tree
src/ai/
├── __init__.py                   (85 linhas)
├── config/
│   ├── __init__.py               (22 linhas)
│   └── settings.py               (85 linhas)
├── core/
│   ├── __init__.py               (12 linhas)
│   └── client.py                 (170 linhas — AIClientProtocol, MockAIClient)
├── models/
│   ├── __init__.py               (28 linhas)
│   ├── event_detection.py        (52 linhas)
│   ├── message_type_selection.py (55 linhas)
│   └── response_generation.py    (81 linhas)
├── prompts/
│   ├── __init__.py               (45 linhas)
│   ├── base_prompts.py           (169 linhas)
│   ├── state_prompts.py          (138 linhas)
│   └── validation_prompts.py     (149 linhas)
├── rules/
│   ├── __init__.py               (22 linhas)
│   └── fallbacks.py              (132 linhas)
├── services/
│   ├── __init__.py               (11 linhas)
│   ├── _orchestrator_helpers.py  (90 linhas)
│   └── orchestrator.py           (181 linhas — AIOrchestrator)
└── utils/
    ├── __init__.py               (24 linhas)
    ├── _json_extractor.py        (63 linhas)
    ├── parser.py                 (151 linhas)
    └── sanitizer.py              (115 linhas)
```

**Observação:** `ai/` não faz mais IO direto. `OpenAIClient` está em `app/infra/ai/`.

### 11.2 Módulo `app/` — 48 arquivos, 2.544 linhas

```tree
src/app/
├── __init__.py
├── app.py
├── bootstrap/                    (198 linhas total)
│   ├── __init__.py               (54 linhas)
│   ├── whatsapp_adapters.py      (102 linhas)
│   └── whatsapp_factory.py       (42 linhas)
├── coordinators/                 (subpastas por canal - stubs)
├── infra/
│   ├── ai/                       (266 linhas total)
│   │   ├── __init__.py           (11 linhas)
│   │   ├── _openai_http.py       (99 linhas)
│   │   └── openai_client.py      (156 linhas — OpenAIClient)
│   ├── crypto/                   (226 linhas total)
│   │   ├── __init__.py           (27 linhas)
│   │   ├── constants.py          (8 linhas)
│   │   ├── errors.py             (11 linhas)
│   │   ├── keys.py               (74 linhas)
│   │   ├── payload.py            (81 linhas)
│   │   └── signature.py          (25 linhas)
│   └── http.py
├── observability/                (87 linhas total)
│   ├── __init__.py               (21 linhas)
│   └── correlation.py            (66 linhas)
├── protocols/                    (356 linhas total)
│   ├── __init__.py               (36 linhas)
│   ├── decision_audit_store.py   (14 linhas)
│   ├── dedupe.py                 (62 linhas)
│   ├── http_client.py            (19 linhas)
│   ├── models.py                 (127 linhas)
│   ├── normalizer.py             (13 linhas)
│   ├── outbound_sender.py        (17 linhas)
│   ├── payload_builder.py        (13 linhas)
│   ├── session_store.py          (38 linhas)
│   └── validator.py              (17 linhas)
├── services/                     (249 linhas total)
│   ├── __init__.py               (12 linhas)
│   ├── _decider_helpers.py       (116 linhas)
│   └── master_decider.py         (121 linhas)
├── sessions/                     (266 linhas total)
│   ├── __init__.py               (13 linhas)
│   ├── manager.py                (103 linhas)
│   └── models.py                 (150 linhas)
└── use_cases/whatsapp/           (511 linhas total)
    ├── __init__.py               (28 linhas)
    ├── _inbound_helpers.py       (124 linhas)
    ├── process_inbound_canonical.py (198 linhas)
    ├── process_inbound_event.py  (98 linhas)
    └── send_outbound_message.py  (63 linhas)
```

### 11.3 Módulo `fsm/` — 11 arquivos, 864 linhas

```tree
src/fsm/
├── __init__.py                   (76 linhas)
├── manager/
│   ├── __init__.py               (17 linhas)
│   └── machine.py                (194 linhas — FSMStateMachine)
├── rules/
│   ├── __init__.py               (25 linhas)
│   └── guards.py                 (176 linhas)
├── states/
│   ├── __init__.py               (21 linhas)
│   └── session.py                (89 linhas — SessionState enum)
├── transitions/
│   ├── __init__.py               (21 linhas)
│   └── rules.py                  (135 linhas — VALID_TRANSITIONS)
└── types/
    ├── __init__.py               (12 linhas)
    └── transition.py             (98 linhas — StateTransition)
```

### 11.4 Módulo `config/` — 34 arquivos, 2.659 linhas

```tree
src/config/
├── __init__.py
├── settings.py                   (17 linhas)
├── logging/                      (305 linhas total)
│   ├── __init__.py               (45 linhas)
│   ├── config.py                 (139 linhas)
│   ├── filters.py                (63 linhas)
│   └── formatters.py             (58 linhas)
└── settings/                     (~2.337 linhas total)
    ├── ai/                       (openai, llm_phases, flood)
    ├── base/                     (core, dedupe, session)
    ├── infra/                    (firestore, gcs, pubsub, cloud_tasks)
    └── [canais].py               (whatsapp, instagram, etc.)
```

### 11.5 Módulo `api/` — 129 arquivos, 3.685 linhas

```tree
src/api/
├── connectors/                   (por canal)
├── normalizers/                  (por canal)
├── payload_builders/             (por destino)
└── validators/                   (por protocolo)
```

---

## 12) Cobertura de Testes por Módulo

| Módulo                               | Cobertura | Status |
| ------------------------------------ | --------- | ------ |
| `fsm/`                               | 97%       | ✅     |
| `ai/` (exceto infra)                 | 95%       | ✅     |
| `config/logging/`                    | 100%      | ✅     |
| `app/use_cases/whatsapp/` (legado)   | 100%      | ✅     |
| `app/use_cases/whatsapp/` (canônico) | 30%       | ⚠️     |
| `app/services/`                      | ~80%      | ✅     |
| `app/sessions/`                      | ~85%      | ✅     |
| `app/infra/ai/`                      | ~74%      | ⚠️     |
| `config/settings/`                   | 0%        | ❌     |
| `app/coordinators/`                  | 0%        | ❌     |

**Arquivos de teste principais:**

| Arquivo                                                | Linhas | Testes |
| ------------------------------------------------------ | ------ | ------ |
| `tests/test_fsm/test_fsm_complete.py`                  | 600    | 23     |
| `tests/api/payload_builders/test_whatsapp_builders.py` | 596    | ~50    |
| `tests/api/validators/test_whatsapp_validators.py`     | 591    | ~40    |
| `tests/test_config/test_logging.py`                    | 295    | 20     |
| `tests/app/services/test_master_decider.py`            | 244    | 8      |
| `tests/app/sessions/test_session_models.py`            | 187    | 13     |
| `tests/test_ai/test_openai_client.py`                  | 185    | 9      |

---

**Relatório preparado por:** Auditor Arquitetural  
**Data:** 02/fev/2026  
**Versão:** 2.9 (OpenAIClient movido para app/infra/ai/)

---

## Changelog

| Versão | Data      | Alterações                                                    |
| ------ | --------- | ------------------------------------------------------------- |
| 2.9    | 02/fev/26 | OpenAIClient movido de ai/core/ para app/infra/ai/ (boundary) |
| 2.8    | 02/fev/26 | Integração AIOrchestrator + ProcessInboundCanonicalUseCase    |
| 2.7    | 02/fev/26 | Refatoração ≤200 linhas (orchestrator.py, parser.py)          |
| 2.6    | 02/fev/26 | FSM e AI implementados, 305 testes                            |
| 2.5    | 01/fev/26 | Criptografia movida para app/infra/crypto                     |
