# FUNCIONAMENTO.md — Atende_Pyloto (Arquitetura e Fluxo Operacional)

> Documento operacional do sistema **Atende_Pyloto**, alinhado a `REGRAS_E_PADROES.md` e à estrutura atual de `src/`.
>
> Foco: **fluxo end-to-end**, **responsabilidades por pasta**, **escala (centenas de requisições simultâneas)**, **multicanais**, **resiliência**, **segurança** e **observabilidade**.

---

## 1) Visão geral do sistema

O **Atende_Pyloto** é um núcleo de atendimento e automação para CRM omnichannel. Ele recebe eventos de múltiplos canais (WhatsApp, Instagram, Facebook, LinkedIn, YouTube, Google Calendar, Apple Calendar, TikTok, Discord e outros), normaliza e valida entradas, aplica regras de negócio e FSM, aciona IA quando apropriado, registra auditoria e envia respostas/ações de forma confiável e idempotente.

**Princípios operacionais:**

- **Alta concorrência:** processa **centenas de requisições simultâneas** com filas/execução assíncrona e IO não bloqueante quando aplicável.
- **Idempotência e dedupe:** entradas e saídas não podem duplicar efeitos.
- **SRP e boundaries:** regras e contratos isolados; infraestrutura não vaza para domain/use cases.
- **Observabilidade:** logs estruturados, métricas, tracing por `correlation_id`.
- **Zero-trust:** toda entrada externa é não confiável; validação e sanitização são obrigatórias.

---

## 2) Estrutura de pastas (src/) e responsabilidades

### 2.1 `src/api/` — Edge/Conectores e Adaptação de Canal

**Responsabilidade:** integrar com provedores/canais, validar assinatura, traduzir eventos do mundo externo para a linguagem interna do sistema e disparar o processamento assíncrono.

Contém:
    - `api/connectors/<canal>/...`
      - Webhooks (recebimento), assinatura/segurança, clients HTTP do provedor, helpers de mídia, builders de payload outbound específicos.
    - `api/normalizers/`
      - Normalização de payloads externos para formas internas (por provedor).
    - `api/payload_builders/`
      - Construção de payloads outbound por provedor (texto, mídia, template, interação etc.).
    - `api/validators/`
      - Validações específicas dos provedores (limites, compatibilidade de payload).

**Regra:** `api/` não contém regra de negócio do CRM. Apenas **adaptação** e **integração**.

### 2.2 `src/app/` — Core de Aplicação (orquestração do domínio)

**Responsabilidade:** coordenar casos de uso, políticas, sessões, dedupe, fila/outbox, handoff e integração com o FSM e IA.

Subpastas (lógica sugerida e já alinhada com o seu tree):
    - `app/bootstrap/` — composição do sistema (wiring), factories, container/DI, inicialização.
    - `app/coordinators/` — orquestração de fluxos (ex.: inbound flow, outbound flow, handoff flow).
    - `app/use_cases/` — casos de uso (ex.: processar evento inbound, enviar mensagem outbound, registrar decisão IA).
    - `app/services/` — serviços de aplicação (ex.: dedupe manager, outbox, scheduler, rate limiting).
    - `app/sessions/` — ciclo de vida de sessão (load/create, append idempotente, persistência via infra).
    - `app/policies/` — políticas determinísticas (anti-abuso, roteamento, thresholds, fallback).
    - `app/protocols/` — contratos usados por `app/` para falar com infra (stores, queues, http, secrets).
    - `app/infra/` — somente implementações infra necessárias ao app (ex.: adapters de store, cache, filas).
    - `app/observability/` — logging/tracing/metrics (wrappers, middlewares e helpers).
    - `app/constants/` — constantes globais da aplicação (nomes de headers, keys, timeouts).
    - `app/app.py` — entrypoint de execução da aplicação (não confundir com web framework).

**Regra:** `app/` não importa `api/` como regra; `api/` chama `app/`.

### 2.3 `src/ai/` — IA (prompts, contratos e serviços)

**Responsabilidade:** tudo relacionado a IA (LLMs) **sem vazar** para connectors ou infra diretamente.

- `ai/prompts/` — prompts organizados por tipo (base/state/validation).
- `ai/models/` — contratos/datatypes de entrada/saída de IA.
- `ai/services/` — clientes e serviços (ex.: OpenAI client wrapper, parsers, schemas).
- `ai/rules/` — regras determinísticas relacionadas a IA (fallback, thresholds, validação de resposta).
- `ai/core/` — orquestração interna de IA (ex.: pipeline IA, compondo etapas).
- `ai/config/` — configurações específicas da IA.
- `ai/utils/` — helpers (sanitização de contexto, truncamento, schema tooling).

**Regra:** IA nunca é fonte de verdade para invariantes (ex.: segurança, idempotência, validação de assinatura).

### 2.4 `src/fsm/` — Máquina de Estados

**Responsabilidade:** estados, transições e regras determinísticas do atendimento.

- `fsm/states/` — enum/objetos de estados.
- `fsm/transitions/` — regras de transição.
- `fsm/rules/` — guards e invariantes.
- `fsm/manager/` — executor/aplicador de transições e helpers.

### 2.5 `src/config/` — Configuração e Settings

**Responsabilidade:** settings por provedor e configuração base do sistema.

- `config/settings.py` e `config/settings/*.py` — settings tipados.
- `config/logging/` — config de logging.

### 2.6 `src/utils/` — Utilitários comuns (genéricos e puros)

**Responsabilidade:** funções auxiliares puras e comuns (audit, ids, timing, errors).

- Sem dependência de `api/` ou de provedores.
- Sem efeito colateral relevante, exceto helpers de observabilidade/audit.

---

## 3) Modelo operacional: eventos, comandos e efeitos

O sistema trabalha com 3 coisas:
    1. **Eventos inbound** (chegam dos canais)
    2. **Comandos internos** (processar, persistir, decidir, enviar)
    3. **Efeitos/outbound** (mensagens, atualizações em CRM, triggers, calendários etc.)

O objetivo é garantir:
    - **Exatamente-uma-vez por efeito observável** (na prática: *at-least-once* na fila + idempotência no handler)
    - **Ordem consistente por sessão** (quando necessário)
    - **Sem bloquear webhooks/edges** com processamento pesado

---

## 4) Fluxo Inbound (alto nível)

### 4.1 Recebimento (Edge)

1. **Webhook recebe** a requisição (ex.: WhatsApp Graph API).
2. Validações obrigatórias no edge:
   - assinatura/HMAC/token do provedor
   - validação estrutural mínima do JSON
   - extração de `correlation_id` (ou criação)
3. Extrai **eventos** (um webhook pode conter vários).
4. Gera `inbound_event_id` (por `message_id` do provedor ou hash determinístico).
5. Enfileira para processamento assíncrono (fila/Cloud Tasks/worker).

**Invariantes:**
    - O webhook deve responder rápido.
    - Nenhuma chamada de IA ocorre no webhook.
    - Nenhuma persistência pesada ocorre no webhook (apenas dedupe rápido se necessário).

### 4.2 Normalização e validação (Pipeline Inbound)

Ao processar o job:
    1. **Extractor** (payload bruto → estrutura interna)
    2. **Sanitizer** (remove/mascara PII onde aplicável)
    3. **Validator** (regras do provedor: limites e consistência)
    4. **Normalizer** (mapeia para modelos internos: `NormalizedEvent` / `NormalizedMessage`)

> Exemplo: a pasta `api/normalizers/graph_api/` e/ou `api/connectors/whatsapp/inbound/normalize.py` seguem esse conceito.

### 4.3 Dedupe + Anti-abuso + Sessões

1. **Dedupe inbound** (por `inbound_event_id` / `message_id`)
2. **Anti-abuso** (rate limiting, flood, spam heurístico determinístico)
3. **SessionManager**:
   - load_or_create session (por usuário + canal + tenant)
   - append inbound **idempotente** por `message_id`
   - normalizar estado atual (fallback se inválido)
4. Encaminhar para `UseCase: process_inbound_event`

### 4.4 FSM + Políticas + IA (quando aplicável)

1. FSM avalia estado atual e transições possíveis.
2. Políticas determinísticas decidem:
   - ignorar/encerrar por abuso
   - handoff humano
   - self-serve
   - seguir para IA (quando permitido)
3. Se IA habilitada:
   - etapa(s) de seleção de estado / geração / validação (conforme arquitetura atual do seu `ai/`)
   - validação de saída e fallback seguro
4. Persistência:
   - atualizar sessão
   - registrar auditoria (decisões e justificativas, sem PII)

---

## 5) Fluxo Outbound (alto nível)

1. Use case produz um `OutboundCommand` (ex.: enviar mensagem).
2. Builder do provedor gera payload:
   - `api/payload_builders/<provedor>/...`
3. **Dedupe outbound** por `idempotency_key` (hash do payload + contexto) com TTL configurável.
4. Enfileirar job de envio (outbound worker).
5. Handler outbound:
   - valida payload novamente
   - executa HTTP com circuit breaker + retry controlado
   - registra status (sent, failed, retrying)
   - logs estruturados e métricas

**Invariantes:**
    - reprocessamento não duplica envio (idempotência).
    - erros permanentes (4xx) não ficam em retry infinito.
    - erros transientes (5xx/429) respeitam backoff e circuito.

---

## 6) Concorrência e escalabilidade (centenas de requisições simultâneas)

### 6.1 Estratégia de escalabilidade

- **Edge stateless:** `api/` não guarda estado em memória como fonte de verdade.
- **Workers assíncronos:** processamento pesado fora do webhook.
- **Stores compartilhados:** sessões, dedupe e auditoria persistidos em backend (redis/firestore/sql conforme config).
- **Idempotência:** reexecução não causa efeitos duplicados.
- **Separação de filas:** inbound e outbound podem ter filas separadas (e prioridades distintas).

### 6.2 Controle de concorrência por sessão

Dependendo do canal, é comum receber eventos concorrentes do mesmo usuário.
Soluções aceitáveis:
    - **Lock por sessão** (leve, com TTL curto) no store (ex.: redis lock)
    - **Sequenciamento por chave** (fila particionada por user_key)
    - **Detecção de conflito** na persistência (versão/ETag) e retry seguro

### 6.3 Timeouts e limites

- Toda operação externa tem timeout.
- IA tem timeout + fallback determinístico.
- Circuit breaker evita cascata.
- Payloads têm limites de tamanho e validação.

---

## 7) Multicanal (WhatsApp, Instagram, Facebook, LinkedIn, YouTube, Google/Apple Calendar, TikTok, Discord)

### 7.1 Conceito: “conector”

Cada canal é um **conector** com três responsabilidades:

1. **Inbound**: receber/validar e transformar em eventos internos
2. **Outbound**: construir payload e enviar (ou agendar ações)
3. **Modelos/erros**: tipos específicos e mapeamentos

**Local sugerido:**

- `api/connectors/<canal>/...`
- `api/normalizers/<provedor>/...`
- `api/payload_builders/<provedor>/...`
- `api/validators/<provedor>/...`

### 7.2 Eventos internos padronizados

Independentemente do canal, o sistema tenta convergir para um conjunto de eventos internos, por exemplo:

- `MessageReceived`
- `MessageDelivered`
- `MessageRead`
- `MediaUploaded`
- `CalendarEventCreated/Updated`
- `CommentReceived` (YouTube/LinkedIn/TikTok)
- `ReactionReceived`

Isso reduz complexidade no `app/` e facilita expansão de canais.

---

## 8) Observabilidade e auditoria

### 8.1 Logs estruturados

Todo log relevante inclui:

- `correlation_id`
- `channel`
- `tenant_id` (quando aplicável)
- `session_id`
- `event_id` / `idempotency_key`
- `outcome` / `status`

**PII proibida** em logs: telefone, email, documentos, conteúdo completo.

### 8.2 Métricas mínimas

- throughput inbound/outbound
- latência por etapa (normalize, fsm, ai, send)
- taxa de dedupe
- taxa de circuit breaker open
- erros por classe (4xx/5xx/timeouts)
- fila: depth e age

### 8.3 Auditoria

Persistir decisões importantes:

- transições de estado
- decisões de roteamento/handoff
- saída de IA (estruturada e minimizada)
- erros permanentes relevantes

---

## 9) Segurança (resumo operacional)

- validação de assinatura em todo webhook
- autenticação interna entre edge e workers (token/secret)
- sanitização e validação por camada
- rate limiting e anti-abuso determinístico
- secrets via provider (env/secret manager) — nunca hardcoded
- princípio do menor privilégio nos acessos (scopes e credenciais)

---

## 10) Circuit breaker e retry (resiliência)

Para chamadas HTTP a provedores externos:

- circuit breaker com estados `closed / open / half-open`
- retry apenas em transientes (5xx/429/timeouts)
- jitter/backoff para evitar thundering herd
- logs claros do breaker sem dados sensíveis

---

## 11) Compatibilidade e evolução do repositório

- mudanças estruturais devem preservar a API pública de imports sempre que necessário (re-export em `__init__.py`).
- módulos “legados” devem ser marcados explicitamente com docstring `LEGACY` e TODO de remoção futura.
- qualquer exceção a regras (ex.: arquivo >200 linhas) exige justificativa no próprio arquivo e registro em docs.

---

## 12) Checklist operacional (para cada PR)

**Gates obrigatórios (mínimo):**

- `ruff check .`
- `pytest -q`
- `pytest --cov=src --cov-fail-under=<threshold do repo>`

**Checklist de regressão:**

- inbound dedupe não perde eventos
- outbound idempotência não duplica
- sessão não corrompe estado com concorrência
- logs não incluem PII
- fallback determinístico da IA funciona

---

## 13) Apêndice: exemplos de fluxos por canal

### 13.1 WhatsApp (Graph API)

- Inbound: assinatura → extractor/validator → normalize → dedupe → session → fsm/ai → persist → outbound enqueue
- Outbound: payload builder → validator → dedupe outbound → http client (breaker/retry) → status/audit

### 13.2 Instagram/Facebook

- Similar ao WhatsApp (mesmo ecossistema Meta), mas com modelos/limites distintos e eventos adicionais (comentários, reactions).

### 13.3 Calendários (Google/Apple)

- Eventos entram como “calendar event” e disparam use cases (criar/alterar compromissos, reminders, sincronização).
- Outbound pode ser: criar evento, atualizar evento, enviar confirmação em outro canal.

### 13.4 YouTube/LinkedIn/TikTok/Discord

- Eventos típicos: comentário, DM, menção.
- Normalização converte para `MessageReceived` com `channel` distinto.
- Resposta pode ser comentário, DM ou ação interna de CRM.

---

## 14) Onde este documento se encaixa

- `REGRAS_E_PADROES.md` define **o que pode** e **o que não pode**.
- `FUNCIONAMENTO.md` explica **como o sistema opera** e **como as peças se encaixam**.
- `README.md` explica **como rodar** e **como contribuir** (setup/dev/ops).
