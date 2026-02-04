# REGRAS_E_PADROES.md — Atende_Pyloto

Este documento define as **REGRAS ABSOLUTAS, congeladas e não negociáveis** do repositório `Atende_Pyloto`.

- Passar testes **não** compensa violação arquitetural.
- “Funciona na minha máquina” **não** é argumento.
- Segurança assume **zero‑trust**: sempre existirão usuários mal‑intencionados e usuários bem‑intencionados testando limites.

---

## 1) Princípios inegociáveis

### 1.1 Clareza > esperteza

Código deve ser **legível e auditável** por terceiros sem explicação verbal. Abstrações opacas são proibidas.

### 1.2 SRP real

Cada módulo deve ter **um** motivo para mudar. Se você não consegue resumir um arquivo/pasta em **uma frase**, está misturado.

### 1.3 Determinismo e previsibilidade

Comportamento não pode depender de:
    - ordem de execução implícita
    - estado global
    - relógio real sem injeção
    - rede real sem stub/fake
    - aleatoriedade sem seed controlada

### 1.4 Boundaries são lei

Camadas **não se misturam**. Violação é falha arquitetural grave.

### 1.5 Defesa em profundidade

Toda entrada externa é hostil por padrão:
    - validar formato e schema
    - validar limites (tamanho, tipos, ranges)
    - idempotência/dedupe
    - falhar de forma explícita, rastreável e testável

---

## 2) Estrutura do repositório (SRC) e responsabilidades

A estrutura em `src/` é o contrato de organização. Cada pasta tem papel claro; arquivos fora do lugar viram dívida IMEDIATA.

```tree
src/
├── ai/
├── api/
├── app/
├── config/
├── fsm/
└── utils/
```

### 2.1 `src/ai/` — Inteligência (LLM e regras relacionadas)

**Escopo:** LLM, prompts, validações e utilitários específicos de IA.  
**Não pode:** importar `api/` nem fazer IO direto (rede/banco/filesystem).

Subpastas:
    - `ai/config/`: configuração e contratos de IA (modelos, thresholds, timeouts).
    - `ai/core/`: core de execução/orquestração interna de IA (interfaces e pipeline interno de IA).
    - `ai/models/`: modelos/DTOs para IA (entradas/saídas).
    - `ai/prompts/`: prompts versionados:
      - `base_prompts/`: peças reutilizáveis (system/base templates).
      - `state_prompts/`: prompts de seleção de estado/fluxo.
      - `validation_prompts/`: prompts de validação/guardrails.
    - `ai/rules/`: regras determinísticas que não dependem de LLM.
    - `ai/services/`: serviços de alto nível (ex.: classificar intenção, gerar opções).
    - `ai/utils/`: helpers de IA (parsers, normalizadores de output, etc.).

### 2.2 `src/api/` — Interface/Edge (entrada e saída do mundo externo)

**Escopo:** camada de borda e adapters de canais.  
**Responsabilidade:** receber requests, validar assinatura, normalizar payload, construir payloads, aplicar limites/validações de API.

Subpastas:
    - `api/connectors/`: conectores por canal.
      - `api/connectors/whatsapp/`:
        - `webhook/`: receive/verify/signature.
        - `inbound/`: entrada processável (event_id, handler, normalize).
        - `outbound/`: estruturas/rotinas outbound (quando existirem).
        - `outbound_flow/`: fluxo de envio (client e coordenação).
        - módulos locais (`http_client.py`, `signature.py`, `message_builder.py`, etc.) devem ser SRP e pequenos.
    - `api/normalizers/`: normalizadores por fornecedor/protocolo (ex.: `graph_api/`).
    - `api/payload_builders/`: builders por destino (apple/google/graph_api/linkedin/tiktok).
    - `api/validators/`: validações por canal/protocolo (ex.: `validators/graphapi/`).
    - `api/routes/`: rotas HTTP por canal (endpoints FastAPI/Starlette).  
      (Endpoints são adapters de borda — sem lógica de negócio.)

**Não pode:** conter decisão de FSM, regras de sessão, policies globais, ou orquestração de casos de uso. Isso é `app/` e `fsm/`.

### 2.3 `src/app/` — Aplicação (orquestração, casos de uso e infraestrutura interna)

**Escopo:** “coração” do sistema: coordena regras, FSM, IA e infraestrutura.  
**Padrão mental:** `app` executa; `api` adapta; `ai` decide; `fsm` governa; `utils` apoia.

Subpastas:
    - `app/bootstrap/`: composition root (factories, inicialização, wiring).
    - `app/coordinators/`: fluxos end‑to‑end (inbound → pipeline → outbound).
    - `app/use_cases/`: casos de uso (inputs/outputs, sem IO direto).
    - `app/services/`: serviços de aplicação (unidades reutilizáveis de orquestração).
    - `app/infra/`: implementações concretas de IO internas (stores, filas, http, redis, firestore, secrets).
    - `app/protocols/`: contratos/interfaces que o app exige (store, queue, http, etc.).
    - `app/sessions/`: modelos e componentes de sessão (regras de idempotência e persistência via protocolos).
    - `app/policies/`: políticas (rate limit, abuse detection, dedupe/TTL/retry).
    - `app/observability/`: logs estruturados, tracing/correlation, métricas.
    - `app/constants/`: constantes da aplicação (não específicas de canal).

### 2.4 `src/config/` — Configuração e settings

**Escopo:** settings tipados, carregamento de env, defaults, validação de config.
    - `config/settings/`: settings por canal/provedor e agregador.
      - `config/settings/ai/`, `config/settings/base/`, `config/settings/infra/`: subpastas com agrupamentos lógicos de settings (ai, base, infra, e por canal).
    - `config/agents/`: configurações YAML dos agentes LLM (state, response, message_type, decision).
    - `config/logging/`: logging config.

### 2.5 `src/fsm/` — Máquina de estados (domínio determinístico)

**Escopo:** estados, transições e regras determinísticas.
    - `fsm/states/`: definições dos estados.
    - `fsm/transitions/`: transições permitidas.
    - `fsm/rules/`: regras de transição.
    - `fsm/types/`: tipos/DTOs da FSM (ex.: StateTransition, TransitionResult).
    - `fsm/manager/`: aplicação/validação da FSM.

### 2.6 `src/utils/` — Utilitários comuns (cross‑cutting)

**Escopo:** helpers genéricos (sem regra de negócio).
    - `utils/errors/`: exceções tipadas
    - `utils/ids.py`: IDs/fingerprints
    - `utils/audit.py`: helpers de auditoria (sem PII)
    - `utils/timing.py`: medições/latências
    - demais arquivos somente se forem realmente transversais

---

## 3) Separação de camadas

Camadas (conceito):
    1) **Domínio determinístico**: `fsm/` + regras determinísticas em `ai/rules/` + parte determinística de `app/policies/`  
    2) **Orquestração**: `app/use_cases/`, `app/services/`, `app/coordinators/`  
    3) **Infra/IO**: `app/infra/` + adapters em `api/`

Regras práticas:

- `fsm/` não importa `app/infra`, `api/` nem `ai/services`.
- `ai/` não faz IO direto; IO só via protocolos e `app/infra`.
- `api/` não contém regra de negócio; apenas adapta/valida.
- `app/use_cases` não importa implementações concretas de `app/infra` (somente contratos).
- `app/bootstrap` é o único lugar autorizado a “colar” implementações concretas.

Violação = bloqueio.

---

## 4) Limites objetivos de tamanho e complexidade

- Arquivos: **≤200 linhas** (preferência 120–160).
- Funções/métodos: **≤50 linhas**.
- Classes: **≤200 linhas** por arquivo.

Exceção:
    1) fragmentar piora a clareza, e
    2) comentário no topo: `EXCECAO REGRA 2.1: <motivo>` e
    3) registro em `docs/Monitoramento_Regras-Padroes.md`.

---

## 5) Estilo e padrões de código

- Comentários em **PT‑BR** e explicando o **porquê**.
- `snake_case` em arquivos e pastas.
- Tipagem explícita nas fronteiras (inputs/outputs, modelos).
- `Any` apenas quando inevitável e isolado.

---

## 6) Logs, auditoria e PII

- Proibido logar: telefone, e‑mail, documentos, endereço, payload bruto, tokens/headers sensíveis.
- Logs devem ser estruturados e conter: `correlation_id`, `event_id/message_id` quando existir, `component`, `action`, `result`, `latency_ms`.

---

## 7) Segurança e resiliência

- Entradas externas: assinatura + schema + limites + dedupe/idempotência + rate limit/abuse.
- Fail‑fast para erros permanentes; retry limitado para transitórios.
- Circuit breaker onde houver risco de cascata.
- Fallback seguro e determinístico quando LLM falhar.

---

## 8) Testes — regra correta (sem fetiche por “1 teste por função”)

“Cada função precisa de um teste” é uma regra ruim: cria milhares de testes frágeis e não aumenta confiança.

### 8.1 Regra: testamos comportamento e contrato público

Obrigatório:
    - toda funcionalidade **pública** (use case, coordinator, service, policy, handler) deve ter testes cobrindo o contrato;
    - toda regra determinística relevante deve ser testada;
    - helpers internos pequenos só precisam de teste direto se forem não-triviais ou críticos.

**Tradução prática do que você pediu:**  
> se 10 funções conversam entre si para entregar 1 comportamento, você pode (e deve) cobrir isso com 1–3 testes no nível de use case/coordinator, observando efeitos e saídas, sem “um teste por função”.

### 8.2 Pirâmide de testes (prioridade)

1) Unitários: regras determinísticas (`fsm/`, policies, validators, parsers).  
2) Integração de componente: fluxo do caso de uso com fakes/mocks de IO.  
3) E2E real: mínimos e cirúrgicos (somente wiring/integrações críticas).

### 8.3 Cobertura

- Gate mínimo: **80%**.
- Alvo operacional: **85–90%**.
- PR não pode reduzir cobertura sem justificativa registrada.

### 8.4 Regras de qualidade de teste

- determinístico (sem rede real/tempo real)
- asserts sobre saída/efeito observável
- fixtures sem PII
- sem mocks profundos (se precisa mockar 6 níveis, arquitetura está errada)

---

## 9) Gates obrigatórios

Antes de qualquer merge:
    - `ruff check .`
    - `pytest -q`
    - `pytest --cov=src --cov-fail-under=80` (ajuste o path conforme o repo)

Falhou = não mergeia.

---

## 10) Proibições explícitas

- Arquivos `.bak` dentro de `src/` (proibido).
- Duplicação conceitual (mesmo conceito em 2 lugares) = dívida imediata.
- Vazamento de camada (ex.: domínio importando app) = bloqueio.

---

## 11) Definition of Done

Pronto só quando:
    - SRP e boundaries respeitados
    - sem PII em logs/fixtures
    - gates verdes (ruff/pytest/coverage)
    - sem artefatos proibidos
    - testes validam o **contrato** do comportamento alterado
