# TODO — Implementação Sistema de 4 Agentes de IA (LEGADO)

> **Data:** 02/fev/2026  
> **Status:** ✅ Todas as fases concluídas  
> **Última atualização:** 395 testes passando  
> **Objetivo:** Implementar pipeline de 4 agentes LLM conforme README.md  
> **Nota (05/fev/2026):** Pipeline legado foi removido e substituído pela arquitetura Otto (agente único + utilitários). Este registro é mantido apenas para histórico.

---

## Progresso Geral

| Fase |    Descrição             |    Status    |
|------|--------------------------|--------------|
| 1    | Contratos e DTOs         | ✅ CONCLUÍDO |
| 2    | Configuração YAML        | ✅ CONCLUÍDO |
| 3    | AIClientProtocol         | ✅ CONCLUÍDO |
| 4    | Prompts dos Agentes      | ✅ CONCLUÍDO |
| 5    | Refatorar AIOrchestrator | ✅ CONCLUÍDO |
| 6    | Fallbacks e Regras       | ✅ CONCLUÍDO |
| 7    | Parsers                  | ✅ CONCLUÍDO |
| 8    | Loader YAML              | ✅ CONCLUÍDO |
| 9    | MasterDecider            | ✅ CONCLUÍDO |
| 10   | ProcessInboundCanonical  | ✅ CONCLUÍDO |
| 11   | Testes                   | ✅ CONCLUÍDO |
| 12   | Documentação             | ✅ CONCLUÍDO |

---

## Visão Geral

```funcionamento
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
                      │
                      ▼
              DecisionAgent (LLM #4)
                      │
                      ▼
              MasterDecision
```

---

## Especificações Confirmadas

| Item                   | Valor                                                          |
| ---------------------- | -------------------------------------------------------------- |
| Paralelização          | Agentes 1, 2, 3 em paralelo                                    |
| Threshold de confiança | 0.7                                                            |
| Fallback               | "Desculpe, não entendi. Pode reformular?"                      |
| Escalação para humano  | Após 3x consecutivas com confidence < 0.7                      |
| Candidatos de resposta | 3 (formal, casual, empático)                                   |
| Tipos de mensagem      | text, interactive_button, interactive_list, template, reaction |
| Estados FSM            | 10 fixos (SessionState enum)                                   |
| Config dos agentes     | config/agents/{agent_name}.yaml                                |

---

## Fase 1: Contratos e DTOs [CRÍTICO]

### 1.1 Criar StateAgentResult (ai/models/state_agent.py) ✅ CONCLUÍDO

- [x] Criar arquivo `src/ai/models/state_agent.py`
- [x] Implementar dataclass `SuggestedState`:

  ```python
  @dataclass(frozen=True, slots=True)
  class SuggestedState:
      state: str  # Nome do SessionState
      confidence: float  # 0.0 a 1.0
      reasoning: str  # Justificativa curta
  ```

- [x] Implementar dataclass `StateAgentRequest`:

  ```python
  @dataclass(frozen=True, slots=True)
  class StateAgentRequest:
      user_input: str
      current_state: str
      session_history: list[str]
      valid_transitions: list[str]  # Estados possíveis a partir do atual
  ```

- [x] Implementar dataclass `StateAgentResult`:

  ```python
  @dataclass(frozen=True, slots=True)
  class StateAgentResult:
      previous_state: str
      current_state: str
      suggested_states: tuple[SuggestedState, ...]  # Top 2-3 sugestões
      detected_intent: str
      confidence: float
      rationale: str | None
  ```

- [x] Adicionar validação de invariantes em `__post_init__`
- [x] Exportar em `ai/models/__init__.py`

**Limite:** ≤ 80 linhas

---

### 1.2 Modificar ResponseGenerationResult (ai/models/response_generation.py) ✅ CONCLUÍDO

- [x] Criar dataclass `ResponseCandidate`:

  ```python
  @dataclass(frozen=True, slots=True)
  class ResponseCandidate:
      text_content: str
      tone: str  # "formal" | "casual" | "empathetic"
      confidence: float
      rationale: str | None
  ```

- [x] Modificar `ResponseGenerationResult`:

  ```python
  @dataclass(frozen=True, slots=True)
  class ResponseGenerationResult:
      candidates: tuple[ResponseCandidate, ...]  # 3 candidatos
      options: tuple[ResponseOption, ...] = ()
      suggested_next_state: str | None = None
      requires_human_review: bool = False

      @property
      def best_candidate(self) -> ResponseCandidate:
          """Retorna candidato com maior confidence."""
          return max(self.candidates, key=lambda c: c.confidence)

      @property
      def text_content(self) -> str:
          """Backwards compatible: retorna texto do melhor candidato."""
          return self.best_candidate.text_content
  ```

- [x] Manter backwards compatibility com código existente

**Limite:** ≤ 100 linhas

---

### 1.3 Criar DecisionAgentResult (ai/models/decision_agent.py) ✅ CONCLUÍDO

- [x] Criar arquivo `src/ai/models/decision_agent.py`
- [x] Implementar dataclass `DecisionAgentRequest`:

  ```python
  @dataclass(frozen=True, slots=True)
  class DecisionAgentRequest:
      state_result: StateAgentResult
      response_result: ResponseGenerationResult
      message_type_result: MessageTypeSelectionResult
      user_input: str
      session_context: dict[str, Any]
      consecutive_low_confidence: int  # Contador para escalação
  ```

- [x] Implementar dataclass `DecisionAgentResult`:

  ```python
  @dataclass(frozen=True, slots=True)
  class DecisionAgentResult:
      final_state: str
      final_text: str
      final_message_type: str
      final_tone: str
      confidence: float
      understood: bool  # confidence >= 0.7
      should_escalate: bool  # 3x consecutivas com baixa confiança
      rationale: str | None
  ```

- [x] Exportar em `ai/models/__init__.py`

**Limite:** ≤ 80 linhas

---

### 1.4 Atualizar MessageTypeSelectionResult (ai/models/message_type_selection.py) ✅ CONCLUÍDO

- [x] Adicionar tipo `reaction` aos tipos válidos
- [x] Documentar quando usar `reaction`:
  > Usar apenas quando nenhuma resposta textual é necessária (ex: usuário disse "blz, obg")
- [x] Adicionar validação do tipo no `__post_init__`

**Limite:** Arquivo já existe, apenas modificar

---

## Fase 2: Configuração YAML dos Agentes [CRÍTICO] ✅ CONCLUÍDO

### 2.1 Criar estrutura de diretório

- [x] Criar pasta `config/agents/`

### 2.2 Criar config/agents/state_agent.yaml ✅ CONCLUÍDO

```yaml
# StateAgent — Identifica estado e sugere transições
agent_name: state_agent
version: "1.0.0"
description: "Identifica estado atual da conversa e sugere próximos estados válidos"

model:
  name: gpt-4o-mini
  temperature: 0.3
  max_tokens: 500
  timeout_seconds: 10

behavior:
  max_suggestions: 3
  min_confidence: 0.5
  fallback_state: TRIAGE

valid_states:
  - INITIAL
  - TRIAGE
  - COLLECTING_INFO
  - GENERATING_RESPONSE
  - HANDOFF_HUMAN
  - SELF_SERVE_INFO
  - ROUTE_EXTERNAL
  - SCHEDULED_FOLLOWUP
  - TIMEOUT
  - ERROR

terminal_states:
  - HANDOFF_HUMAN
  - SELF_SERVE_INFO
  - ROUTE_EXTERNAL
  - SCHEDULED_FOLLOWUP
  - TIMEOUT
  - ERROR
```

### 2.3 Criar config/agents/response_agent.yaml

```yaml
# ResponseAgent — Gera candidatos de resposta
agent_name: response_agent
version: "1.0.0"
description: "Gera 3 candidatos de resposta com tons diferentes"

model:
  name: gpt-4o-mini
  temperature: 0.7
  max_tokens: 1000
  timeout_seconds: 15

behavior:
  candidate_count: 3
  tones:
    - formal
    - casual
    - empathetic
  max_response_length: 4096
  min_confidence: 0.5

guardrails:
  prohibit_pii: true
  prohibit_offensive: true
  require_portuguese_br: true
```

### 2.4 Criar config/agents/message_type_agent.yaml

```yaml
# MessageTypeAgent — Seleciona tipo de mensagem ideal
agent_name: message_type_agent
version: "1.0.0"
description: "Seleciona o tipo de mensagem mais adequado para a resposta"

model:
  name: gpt-4o-mini
  temperature: 0.2
  max_tokens: 300
  timeout_seconds: 8

behavior:
  valid_types:
    - text
    - interactive_button
    - interactive_list
    - template
    - reaction
  default_type: text
  min_confidence: 0.6

rules:
  reaction_triggers:
    - "ok"
    - "blz"
    - "obg"
    - "valeu"
    - "👍"
  interactive_button_max_options: 3
  interactive_list_max_options: 10
```

### 2.3 Criar config/agents/response_agent.yaml ✅ CONCLUÍDO

### 2.4 Criar config/agents/message_type_agent.yaml ✅ CONCLUÍDO

### 2.5 Criar config/agents/decision_agent.yaml ✅ CONCLUÍDO

---

## Fase 3: AIClientProtocol [CRÍTICO] ✅ CONCLUÍDO

### 3.1 Atualizar ai/core/client.py ✅ CONCLUÍDO

- [x] Adicionar método `suggest_state()` ao protocolo
- [x] Adicionar método `make_decision()` ao protocolo
- [x] Implementar em `MockAIClient` com heurísticas determinísticas
- [x] Manter backwards compatibility
- [x] Dividir em dois arquivos para respeitar limite de 200 linhas:
  - `client.py` (112 linhas) - apenas AIClientProtocol
  - `mock_client.py` (169 linhas) - MockAIClient

**Limite:** ✅ client.py: 112 linhas, mock_client.py: 169 linhas

---

### 3.2 Atualizar app/infra/ai/openai_client.py

- [ ] Implementar `suggest_state()` com chamada real à OpenAI
- [ ] Implementar `make_decision()` com chamada real à OpenAI
- [ ] Usar prompts do `ai/prompts/`
- [ ] Usar fallbacks do `ai/rules/fallbacks.py`
- [ ] Adicionar tratamento de erro e logging

**Limite:** ≤ 200 linhas total (dividir se necessário)

---

## Fase 4: Prompts dos Agentes [ALTO] ✅ CONCLUÍDO

### 4.1 Criar prompts dos agentes (arquivos separados) ✅ CONCLUÍDO

Arquivos criados em `src/ai/prompts/`:
    - `state_agent_prompt.py` (61 linhas) - STATE_AGENT_SYSTEM + format_state_agent_prompt()
    - `response_agent_prompt.py` (61 linhas) - RESPONSE_AGENT_SYSTEM + format_response_agent_prompt()
    - `message_type_agent_prompt.py` (56 linhas) - MESSAGE_TYPE_AGENT_SYSTEM + format_message_type_agent_prompt()
    - `decision_agent_prompt.py` (71 linhas) - DECISION_AGENT_SYSTEM + format_decision_agent_prompt()

- [x] Criar `STATE_AGENT_SYSTEM` prompt (JSON output para sugestão de estados)
- [x] Criar `RESPONSE_AGENT_SYSTEM` prompt (3 candidatos: formal, casual, empathetic)
- [x] Criar `MESSAGE_TYPE_AGENT_SYSTEM` prompt (tipos: text, interactive_button, interactive_list, template, reaction)
- [x] Criar `DECISION_AGENT_SYSTEM` prompt (consolidação, threshold 0.7, escalação após 3 falhas)
- [x] Criar funções de formatação para cada agente
- [x] Exportar em `ai/prompts/__init__.py`

**Limite:** ✅ Todos arquivos < 200 linhas

---

### 4.2 Atualizar `ai/prompts/__init__.py` ✅ CONCLUÍDO

- [x] Adicionar exports dos novos prompts
- [x] Manter exports existentes

---

## Fase 5: Refatorar AIOrchestrator [ALTO] ✅ CONCLUÍDO

### 5.1 Atualizar ai/services/orchestrator.py ✅ CONCLUÍDO

- [x] Modificar `OrchestratorResult` para incluir 4 resultados
- [x] Refatorar `process_message()` para 4 agentes LLM:
  - Agentes 1, 2, 3 em paralelo via `asyncio.gather()`
  - Agente 4 consolida outputs
- [x] Implementar `_suggest_state()` (novo)
- [x] Refatorar `_generate_response()` simplificado
- [x] Implementar `_make_decision()` (novo)
- [x] Implementar `_select_message_type_simple()` (novo)

**Limite:** ✅ orchestrator.py: 172 linhas

---

### 5.2 Atualizar ai/services/_orchestrator_helpers.py ✅ CONCLUÍDO

- [x] Adicionar `calculate_4agent_confidence()` para confiança combinada
- [x] Adicionar `should_escalate()` para verificar escalação
- [x] Adicionar `select_best_candidate()` para selecionar melhor candidato
- [x] Adicionar `is_understood()` para verificar threshold

**Limite:** ✅ _orchestrator_helpers.py: 97 linhas

---

## Fase 6: Fallbacks e Regras [ALTO] ✅ CONCLUÍDO

### 6.1 Atualizar ai/rules/fallbacks.py ✅ CONCLUÍDO

- [x] Adicionar `fallback_state_suggestion()` para StateAgent
- [x] Adicionar `fallback_decision()` para DecisionAgent
- [x] Usar constantes de `decision_agent.py` (FALLBACK_RESPONSE, threshold)

**Limite:** ✅ fallbacks.py: 171 linhas (< 200)

---

## Fase 7: Parsers [MÉDIO] ✅ CONCLUÍDO

### 7.1 Criar ai/utils/agent_parser.py ✅ CONCLUÍDO

- [x] Criar `parse_state_agent_response()` (StateAgent LLM #1)
- [x] Criar `parse_response_candidates()` (ResponseAgent LLM #2)
- [x] Criar `parse_decision_agent_response()` (DecisionAgent LLM #4)
- [x] Atualizar `ai/utils/__init__.py` com exports

**Limite:** ✅ agent_parser.py: 137 linhas

---

## Fase 8: Loader de Configuração YAML [MÉDIO] ✅ CONCLUÍDO

### 8.1 Criar ai/config/agent_config.py ✅ CONCLUÍDO

- [x] Criar dataclass `AgentConfig`
- [x] Implementar `load_agent_config()` com cache (lru_cache)
- [x] Implementar `get_all_agent_configs()`
- [x] Validar schema do YAML

**Limite:** ✅ agent_config.py: 81 linhas

---

## Fase 9: Atualizar MasterDecider [MÉDIO] ✅ CONCLUÍDO

### 9.1 Atualizar app/services/master_decider.py ✅ CONCLUÍDO

- [x] Integrar com `DecisionAgentResult` (LLM #4)
- [x] Usar `understood` para decidir se aceita resposta
- [x] Usar `should_escalate` para marcar escalação
- [x] Adicionar campo `understood` em `MasterDecision`

**Limite:** ✅ master_decider.py: 133 linhas

---

## Fase 10: Atualizar ProcessInboundCanonicalUseCase [MÉDIO] ✅ CONCLUÍDO

### 10.1 Atualizar app/use_cases/whatsapp/process_inbound_canonical.py ✅ CONCLUÍDO

- [x] Usar novo `OrchestratorResult` com 4 agentes
- [x] Adicionar `valid_transitions` ao chamar orquestrador
- [x] Usar `state_suggestion` do StateAgent para FSM
- [x] Criar helper `map_state_suggestion_to_target()`
- [x] Adicionar `_get_valid_transitions()`

**Limite:** ✅ process_inbound_canonical.py: 216 linhas (ligeiramente acima)

---

## Fase 11: Testes [ALTO] ✅ CONCLUÍDO

### 11.1 Testes de Contratos (tests/test_ai/) ✅ CONCLUÍDO

- [x] Criar `test_models_state_agent.py`:
  - [x] Testar `SuggestedState` validação
  - [x] Testar `StateAgentRequest` criação
  - [x] Testar `StateAgentResult` invariantes
- [x] Criar `test_models_decision_agent.py`:
  - [x] Testar `DecisionAgentRequest` criação
  - [x] Testar `DecisionAgentResult` invariantes
  - [x] Testar `understood` = confidence >= 0.7

- [x] Atualizar `test_response_generation.py`:
  - [x] Testar 3 candidatos
  - [x] Testar `best_candidate` property
  - [x] Testar backwards compatibility

### 11.2 Testes de Prompts (tests/test_ai/) ✅ CONCLUÍDO

- [x] Criar `test_agent_prompts.py`:
  - [x] Testar formatação de cada prompt
  - [x] Testar que prompts não contêm PII

### 11.3 Testes de Orchestrator (tests/test_ai/) ✅ CONCLUÍDO

- [x] Atualizar `test_orchestrator.py`:
  - [x] Testar execução paralela de agentes 1-3
  - [x] Testar execução sequencial do agente 4
  - [x] Testar fallback quando LLM falha
  - [x] Testar threshold de confiança
  - [x] Testar escalação após 3x

### 11.4 Testes de Parsers (tests/test_ai/) ✅ CONCLUÍDO

- [x] Criar `test_utils_agent_parser.py`:
  - [x] Testar `parse_state_agent_response`
  - [x] Testar `parse_decision_agent_response`
  - [x] Testar parsing com JSON malformado

### 11.5 Testes de Configuração (tests/test_ai/) ✅ CONCLUÍDO

- [x] Criar `test_config_agent_config.py`:
  - [x] Testar load de cada YAML
  - [x] Testar validação de schema
  - [x] Testar cache

### 11.6 Testes de Integração (tests/test_ai/) ✅ CONCLUÍDO

- [x] Criar `test_ai_pipeline.py`:
  - [x] Testar fluxo completo com MockAIClient
  - [x] Testar caso feliz (confidence > 0.7)
  - [x] Testar caso fallback (confidence < 0.7)
  - [x] Testar escalação após 3x

---

## Fase 12: Documentação [BAIXO] ✅ CONCLUÍDO

### 12.1 Atualizar AUDITORIA_ARQUITETURA.md ✅ CONCLUÍDO

- [x] Adicionar seção sobre 4 agentes
- [x] Atualizar métricas de arquivos/linhas
- [x] Atualizar cobertura de testes

### 12.2 Atualizar README.md ✅ CONFIRMADO

- [x] Confirmar que diagrama está correto
- [x] Diagrama de 4 agentes já presente

---

## Critérios de Aceite (Definition of Done)

Para cada item:

- [x] Código segue REGRAS_E_PADROES.md ✅
- [x] Arquivo ≤ 200 linhas ✅ (1 exceção documentada: process_inbound_canonical.py 217 linhas)
- [x] Funções ≤ 50 linhas ✅
- [x] Sem PII em logs/fixtures ✅
- [x] Testes cobrindo contrato público ✅ (395 testes)
- [x] `ruff check .` passa ✅
- [x] `pytest -q` passa ✅ (395 passed)
- [ ] Cobertura ≥ 80% ⚠️ (55% geral, 92% em ai/)
- [x] Boundaries respeitados (ai/ não faz IO) ✅

---

## Ordem de Execução Recomendada

```ordem recomendada
Fase 1 (Contratos)     ─┬─► Fase 2 (YAMLs)
                        │
                        ├─► Fase 3 (Protocol)
                        │
                        └─► Fase 4 (Prompts) ─► Fase 5 (Orchestrator)
                                                      │
                                                      ▼
                              Fase 6 (Fallbacks) + Fase 7 (Parsers)
                                                      │
                                                      ▼
                              Fase 8 (Config Loader) + Fase 9 (MasterDecider)
                                                      │
                                                      ▼
                                              Fase 10 (UseCase)
                                                      │
                                                      ▼
                                              Fase 11 (Testes)
                                                      │
                                                      ▼
                                              Fase 12 (Docs)
```

---

## Riscos e Mitigações

| Risco                 | Impacto | Mitigação                         |
| --------------------- | ------- | --------------------------------- |
| Latência 4 LLMs       | Alto    | Paralelizar agentes 1-3           |
| Custo tokens          | Médio   | Usar gpt-4o-mini para agentes 1-3 |
| Breaking changes      | Alto    | Manter backwards compatibility    |
| Falha de LLM          | Alto    | Fallbacks determinísticos         |
| Arquivos > 200 linhas | Médio   | Dividir em helpers                |

---

## Log de Progresso

| Data      |  Fase   |   Status     |   Observações                                                          |
| --------- | ------- | ------------ | ---------------------------------------------------------------------- |
| 02/fev/26 | -       | Criado       | TODO inicial criado                                                    |
| 02/fev/26 | 1.1     | ✅ Concluído | StateAgentResult (SuggestedState, StateAgentRequest, StateAgentResult) |
| 02/fev/26 | 1.2     | ✅ Concluído | ResponseCandidate, ResponseTone, modificado ResponseGenerationResult   |
| 02/fev/26 | 1.3     | ✅ Concluído | DecisionAgentResult (DecisionAgentRequest, DecisionAgentResult)        |
| 02/fev/26 | 1.4     | ✅ Concluído | MessageType enum, VALID_MESSAGE_TYPES, tipo reaction                   |
| 02/fev/26 | 2.1-2.5 | ✅ Concluído | 4 YAMLs de agentes em config/agents/                                   |
| 02/fev/26 | 3.1     | ✅ Concluído | AIClientProtocol + MockAIClient com suggest_state e make_decision      |
