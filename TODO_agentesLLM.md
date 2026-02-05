# TODO — Refatoração de Agentes LLM (Otto + Utilitários)

**Data:** 05 de fevereiro de 2026  
**Origem:** `Auxiliar_TODOrefatoracaoAgentes.md` + `TODO_refatoracao_agentes.md`  
**Objetivo:** remover o pipeline atual de múltiplos agentes e adotar:

1. **TranscriptionAgent** (utilitário, somente quando `message_type=audio`)
2. **ContactCardExtractorAgent** (utilitário, extrai dados do turno)
3. **OttoAgent** (agente principal, único responsável por decidir + responder)

---

## Arquitetura alvo (resumo)

```Fluxo
Inbound (Webhook) -> Normalize -> ProcessInboundCanonicalUseCase
    -> se áudio: TranscriptionAgent -> text
    -> carregar ContactCard (Firestore)
    -> paralelo: (ContactCardExtractorAgent) + (OttoAgent)
    -> merge patch -> persistir ContactCard (Firestore)
    -> validar decisão (determinístico + thresholds)
    -> enviar resposta + atualizar sessão
```

**Nota de camadas (REGRAS_E_PADROES.md):**

- `src/ai/` **não faz IO direto**. IO (OpenAI/WhatsApp/Firestore) fica em `src/app/infra/` e entra via protocolos.
- Logs/fixtures **sem PII** (não logar `wa_id`, telefone, e-mail, endereço, payload bruto).

---

## Mudança de naming (obrigatória)

- **LeadProfile** (nome atual no código) → **ContactCard** (novo nome)
- O que antes era “LeadProfileAgent/LeadProfileExtraction” vira **ContactCardExtractor**.

Checklist de renomeação (find/replace guiado, com testes):

- [x] Definir nomes canônicos: `ContactCard`, `ContactCardPatch`, `ContactCardStore`
- [x] Mapear e renomear usos de `LeadProfile` em:
  - [x] `src/app/domain/lead_profile.py`
  - [x] `src/app/sessions/models.py`
  - [x] `src/app/sessions/manager.py`
  - [x] `src/app/use_cases/whatsapp/process_inbound_canonical.py`
  - [x] `src/ai/models/lead_profile_extraction.py`
  - [x] `src/ai/prompts/lead_profile_agent_prompt.py`
  - [x] `src/app/infra/stores/lead_profile_store.py`
  - [x] `src/app/protocols/lead_profile_store.py`
- [x] Manter compat temporária (se necessário): `LeadProfile = ContactCard` (alias) por 1 release, com TODO de remoção.

---

## ContactCard (modelo + Firestore)

### Estrutura alvo

```tree - ContactCard
Firestore
└── lead_contacts/                    # Collection
    ├── {wa_id}/                      # Document ID = wa_id (ex: "5544988887777")  # vem do webhook
    │   ├── wa_id: "5544988887777"
    │   ├── phone: "5544988887777"
    │   ├── whatsapp_name: "João Silva"        # extraído / o nome que vem do webhook não é necessariamente o nome real
    │   ├── full_name: "Dr. João Pedro Silva"  # extraído
    │   ├── email: "joao@clinica.com"          # extraído
    │   ├── company: "Clínica Saúde Plus"      # extraído
    │   ├── primary_interest: "saas"           # extraído (critério principal p/ contexto)
    │   ├── others_interests: "sob medida + automação"  # extraído (ou lista, decidir)
    │   ├── qualification_score: 65.0          # calculado
    │   ├── is_qualified: true                 # calculado (>= 60)
    │   ├── first_contact_at: Timestamp(...)
    │   ├── last_updated_at: Timestamp(...)
    │   └── ...
```

### Fonte de cada campo

- **Sempre do webhook (não extrair via LLM):**
  - `wa_id` (mesmo valor de `messages[0].from`)
  - `phone` (igual a `wa_id`)
  - `whatsapp_name` (`contacts[0].profile.name`)
- **Extraído pelo ContactCardExtractorAgent (somente se explícito na mensagem):**
  - `full_name`, `email`, `company`, `primary_interest`, `others_interests`, `role`, `location`, etc.
- **Calculado localmente (determinístico):**
  - `qualification_score`, `is_qualified`, `total_messages`, timestamps.

### Tarefas (P0)

- [x] **Modelo:** criar `src/app/domain/contact_card.py` (ou renomear o atual `lead_profile.py`) com:
  - [x] Campos mínimos do schema acima (tipagem completa)
  - [x] `calculate_qualification_score()` (baseado no blueprint do `Auxiliar_TODOrefatoracaoAgentes.md`)
  - [x] `to_prompt_summary()` (max ~200 tokens; foco em interesse/necessidade/score)
  - [x] `to_firestore_dict()` (não persistir `None`)
  - [x] `from_firestore_dict()`
- [x] **Store/Repository:** criar protocolo `src/app/protocols/contact_card_store.py`:
  - [x] `get_or_create(wa_id, whatsapp_name)` / `get(wa_id)` / `upsert(contact_card)`
- [x] Implementar Firestore store em `src/app/infra/stores/firestore_contact_card_store.py`:
  - [x] Collection `lead_contacts`
  - [x] Doc ID = `wa_id`
  - [x] Upsert com `merge=True`
  - [x] Não bloquear fluxo principal: usar `asyncio.to_thread` (SDK Firestore é sync)
- [x] **Normalizer:** estender normalização do WhatsApp para expor `whatsapp_name`:
  - [x] Extrair `contacts[0].profile.name` em `src/api/normalizers/whatsapp/extractor.py`
  - [x] Propagar em `src/api/normalizers/whatsapp/normalizer.py`
  - [x] Expor no contrato `src/app/protocols/models.py` (ex.: `NormalizedMessage.whatsapp_name`)
  - [x] Garantir que não quebra outros canais/tipos
- [x] **PII:** garantir que logs nunca imprimem `wa_id`, `phone`, `email` (usar mask parcial quando inevitável).

---

## Agente utilitário 1 — TranscriptionAgent (áudio)

### Contrato

- **Input:** `media_id` (preferencial) ou `media_url` + metadata (`mime_type`) + `wa_id`
- **Output:** `text` + `language` + `duration_seconds` (se disponível) + `confidence` (heurística) + `error`
- **Fallback:** retornar texto placeholder e `confidence=0.0` sem travar o pipeline

### Tarefas (P0)

- [x] Criar protocolo `src/app/protocols/transcription_service.py` (ou em `src/ai/core/` se for tratado como “IA utilitária”):
  - [x] `async def transcribe_whatsapp_audio(*, media_id: str, wa_id: str) -> TranscriptionResult`
- [x] Implementar download de mídia WhatsApp (Graph API):
  - [x] Criar helper em `src/app/infra/whatsapp/media_downloader.py`
  - [x] Fluxo: `GET /{media_id}` → recebe `url` → download bytes com `Authorization: Bearer`
  - [x] Timeout e retries curtos (30s máx)
- [x] Implementar transcrição Whisper (OpenAI):
  - [x] Usar OpenAI SDK (`openai>=1.58.0`) em `src/app/infra/ai/whisper_client.py`
  - [x] Modelo: `whisper-1`
  - [x] Aceitar OGG/Opus (converter para mp3/wav apenas se necessário; documentar)
- [x] Integrar no fluxo inbound:
  - [x] Em `src/app/use_cases/whatsapp/process_inbound_canonical.py`: se `msg.message_type == "audio"`, transcrever e preencher `sanitized_input`
  - [x] Se confidence < 0.6: responder pedindo texto (não chamar Otto)
- [x] Testes:
  - [x] `tests/app/services/test_transcription_agent.py` com mocks de WhatsApp download + OpenAI

---

## Agente utilitário 2 — ContactCardExtractorAgent (preenchimento do ContactCard)

### Requisito de prompt (do usuário)

O extractor **deve** receber no prompt:

- o **ContactCard atual** (serializado)
- a **mensagem atual do usuário**
- instruções para **procurar/extrair somente informações que ainda não existem** no ContactCard (e nunca inventar)

### Output recomendado

Retornar um **patch** (não o card inteiro), para facilitar merge e auditoria:

- `updates`: dict com campos (somente os novos)
- `confidence`: 0.0–1.0
- `evidence`: opcional (trechos curtos, sem PII, se útil p/ debug interno)

### Tarefas (P0)

- [x] Definir contrato em `src/ai/models/contact_card_extraction.py`:
  - [x] `ContactCardExtractionRequest(contact_card_summary, user_message, conversation_context?)`
  - [x] `ContactCardPatch` (Pydantic) com campos opcionais: `full_name`, `email`, `company`, `primary_interest`, `others_interests`, etc.
- [x] Criar prompt versionado em `src/ai/prompts/contact_card_extractor_prompt.py`:
  - [x] Regra: **não sobrescrever** campos já preenchidos
  - [x] Regra: extrair somente o que estiver **explicitamente** na mensagem
  - [x] Regra: retornar **JSON válido** no schema do patch
- [x] Criar cliente LLM (IO) em `src/app/infra/ai/contact_card_extractor_client.py`:
  - [x] Implementar structured outputs (preferencial) ou JSON strict
  - [x] Modelo barato/rápido (ex.: `gpt-4o-mini`)
  - [x] Timeout curto (5–8s)
- [x] Criar serviço em `src/ai/services/contact_card_extractor.py` que:
  - [x] Monta prompt com ContactCard + user_message
  - [x] Chama o client via protocolo
  - [x] Valida patch (Pydantic) e normaliza (email lowercase, etc.)
- [x] Merge strategy (determinístico) em `src/app/services/contact_card_merge.py`:
  - [x] Preencher somente campos vazios (exceto `urgency`, que pode atualizar)
  - [x] Atualizar `qualification_score` e `is_qualified`
  - [x] Atualizar timestamps
- [x] Persistência:
  - [x] `upsert(contact_card)` após aplicar patch (fire-and-forget aceitável)
- [x] Testes:
  - [x] `tests/test_ai/test_contact_card_extractor.py` (sem rede; mock do client)
  - [x] Casos: sem updates, email, nome completo, interesse primário, múltiplos interesses

---

## Agente principal — OttoAgent

### Responsabilidades

- Decidir **próximo estado** (FSM)
- Gerar **resposta** (texto)
- Selecionar **tipo de mensagem** (`text`, `interactive_button`, `interactive_list`)
- Indicar `confidence` + flags de escalação quando necessário

### Tarefas (P0)

- [ ] Definir contrato em `src/ai/models/otto.py`:
- [x] Definir contrato em `src/ai/models/otto.py`:
  - [x] `OttoRequest(user_message, session_state, history, contact_card_summary, tenant_context, valid_transitions)`
  - [x] `OttoDecision(next_state, response_text, message_type, confidence, requires_human, reasoning_debug?)`
- [x] Criar prompt versionado em `src/ai/prompts/otto_prompt.py`:
  - [x] Injetar: contexto institucional + resumo do ContactCard + histórico curto
  - [x] Guardrails: PT-BR, sem promessas proibidas, sem PII em logs, sem instruções inseguras
- [x] Implementar cliente LLM (IO) em `src/app/infra/ai/otto_client.py`:
  - [x] Structured outputs (preferencial; evita `ai/utils/agent_parser.py`)
  - [x] Modelo principal (ex.: `gpt-4o` ou equivalente com structured outputs)
  - [x] Timeout 10–15s
- [x] Implementar serviço em `src/ai/services/otto_agent.py`:
  - [x] Monta request e chama client via protocolo
  - [x] Valida transição FSM (usar `fsm/` como fonte de verdade)
  - [x] Fallback seguro em exceções (handoff humano)
- [x] Validação híbrida (recomendado do blueprint):
  - [x] Gate determinístico obrigatório (FSM válida, tamanho resposta, PII, promessas proibidas)
  - [x] Thresholds: aprovar alto, escalar baixo, revisão LLM opcional no “cinza”

---

## Integração no fluxo inbound (wiring)

### Tarefas (P0)

- [x] Reescrever `src/app/use_cases/whatsapp/process_inbound_canonical.py` para o novo pipeline:
  - [x] Aceitar `audio` (não retornar `None` só porque `msg.text` é vazio)
  - [x] Resolver/Carregar ContactCard (Firestore) por `wa_id = msg.from_number`
  - [x] Se áudio: transcrever antes de chamar Otto/Extractor
  - [x] Executar em paralelo: `ContactCardExtractorAgent` + `OttoAgent`
  - [x] Aplicar patch no ContactCard e persistir
  - [x] Enviar resposta (usar `decision.message_type`)
- [x] Atualizar `src/app/bootstrap/whatsapp_factory.py` (e/ou `src/app/bootstrap/dependencies.py`):
  - [x] Instanciar Firestore client (já existe factory)
  - [x] Instanciar ContactCardStore (Firestore)
  - [x] Instanciar TranscriptionAgent (WhatsApp downloader + Whisper client)
  - [x] Instanciar Otto client + ContactCardExtractor client
  - [x] Remover dependências do pipeline antigo (AIOrchestrator + MasterDecider se ficar obsoleto)

---

## Remoção do pipeline antigo (limpeza)

> Fazer após o novo pipeline estar rodando (feature flag opcional).

### Tarefas (P1)

- [x] Remover/depreciar 5-agent pipeline:
  - [x] `src/ai/services/orchestrator.py`
  - [x] `src/app/infra/ai/openai_client.py` (ou mover para `legacy_openai_client.py` e depois deletar)
  - [x] `src/ai/utils/agent_parser.py`
  - [x] `src/ai/services/_orchestrator_helpers.py`
  - [x] Prompts antigos em `src/ai/prompts/*_agent_prompt.py` (state/response/message_type/decision/lead_profile)
  - [x] Models antigos em `src/ai/models/*` que não forem mais usados
- [x] Remover YAMLs antigos se estiverem sem uso:
  - [x] `src/config/agents/state_agent.yaml`
  - [x] `src/config/agents/response_agent.yaml`
  - [x] `src/config/agents/message_type_agent.yaml`
  - [x] `src/config/agents/decision_agent.yaml`
- [x] Atualizar exports/imports: `src/ai/__init__.py`, `src/ai/prompts/__init__.py`, `src/ai/models/__init__.py`

---

## Contextos por vertente (ContextInjector)

> Fazer após a limpeza do pipeline antigo, para evitar mexer em prompts/modelos legados.

### Tarefas (P1)

- [x] Alinhar IDs das verticais (YAML ↔ enum):
  - [x] Revisar `src/ai/contexts/institutional_context.yaml` (`servicos_resumo` e `dynamic_context_rules`)
  - [x] Decidir mapeamento para `ContactCard.primary_interest`: `gestao_perfis_trafego`
  - [x] Padronizar nomes: `automacao_atendimento` vs `automacao`, `intermediacao` vs `intermediacao_entregas`
- [x] Completar arquivos de contexto em `src/ai/contexts/verticals/` para todas as verticais suportadas:
  - [x] `saas_pyloto.yaml`
  - [x] `intermediacao_entregas.yaml`
  - [ ] (se optar por separar) `gestao_perfis.yaml` e `trafego_pago.yaml` (mantido combinado)
- [x] Criar loader cacheado do contexto vertical (sem rede) em `src/ai/config/vertical_context_loader.py`
- [x] Criar `ContextInjector` (serviço puro) em `src/ai/services/context_injector.py`:
  - [x] Entrada: `primary_interest` (ou `ContactCard`)
  - [x] Saída: string curta (<= ~1200 chars) pronta para prompt
  - [x] Fallback seguro quando não houver vertical definida
- [x] Integrar no pipeline:
  - [x] Popular `OttoRequest.tenant_context` com contexto vertical selecionado (em `src/app/use_cases/whatsapp/_inbound_processor.py`)
  - [ ] (Opcional) Incluir contexto vertical também no extractor, se aumentar precisão
- [x] Testes:
  - [x] `tests/test_ai/test_context_injector.py` (mapping, fallback, limite de tamanho)

---

## DecisionValidator (3-gate) — separar do OttoAgent

### Tarefas (P1)

- [x] Extrair gate determinístico de `src/ai/services/otto_agent.py` para `src/ai/services/decision_validator.py`
- [x] Definir modelo de validação em `src/ai/models/validation.py` (ex.: `ValidationResult`, `EscalationReason`)
- [x] Implementar Gate 2 (thresholds) e Gate 3 (LLM review seletivo) sem violar boundaries:
  - [x] Protocolo do reviewer em `src/app/protocols/decision_review_client.py`
  - [x] Implementação IO em `src/app/infra/ai/decision_review_client.py` (modelo barato, timeout curto)
- [x] Atualizar pipeline canônico para usar o validator antes do envio outbound
- [x] Testes unitários do validator + integração no `ProcessInboundCanonicalUseCase`

---

## LGPD / PII — auditoria de logs

### Tarefas (P1)

- [ ] Definir helpers únicos de máscara (wa_id/telefone/email) e padronizar uso em logs
- [ ] Auditar `logger.*` em `src/` para garantir que nenhum campo PII vai em `extra`
- [ ] Garantir que access log do Uvicorn permaneça desabilitado em Cloud Run (evita logar querystring do webhook)
- [ ] Adicionar verificação automatizada (script ou teste) para bloquear regressões

---

## Fast-Path determinístico (saudações/FAQ)

### Tarefas (P2)

- [ ] Implementar classificador simples em `src/app/services/fast_path_classifier.py` (sem LLM)
- [ ] Integrar no inbound: se fast-path casar, responder sem chamar Otto/Extractor
- [ ] Medir impacto (latência/custo) via logs/métricas (sem PII)
- [ ] Testes unitários + integração

---

## Resiliência de IO (OpenAI/WhatsApp)

### Tarefas (P2)

- [ ] Implementar circuit breaker leve para chamadas externas (OpenAI e WhatsApp)
- [ ] Padronizar retries e timeouts curtos (evitar cascata)
- [ ] Logar métricas de falha sem PII (`component`, `action`, `result`, `latency_ms`)

---

## Documentação e alinhamento final

### Tarefas (P2)

- [ ] Atualizar `README.md` e exemplos (fast-path, ContextInjector, DecisionValidator) após implementação
- [ ] Remover referências a `LeadProfile` e ao pipeline antigo em comentários/docs remanescentes
- [ ] Revisar `src/app/use_cases/whatsapp/_inbound_helpers.py` para remover tipos/fluxos legados após a limpeza

---

## Testes e critérios de aceite

### Gates obrigatórios (DoD)

- [ ] `ruff check .` sem erros
- [x] `pytest -q` 100% verde
- [ ] Cobertura >= 80% nos serviços novos/alterados (pelo menos merges determinísticos + validator/injector/fast-path)

### Testes recomendados (P0/P1)

- [ ] Unitários:
  - [ ] merge patch → ContactCard (determinístico)
  - [ ] validação gate 1 (PII/promessas/FSM)
  - [ ] ContextInjector (mapping + fallback)
  - [ ] Fast-path classifier
- [ ] Integração:
  - [ ] `ProcessInboundCanonicalUseCase`: texto simples (fast path) + extração + otto
  - [ ] áudio: transcrição → otto
  - [ ] `ProcessInboundCanonicalUseCase`: contexto vertical aplicado (quando `primary_interest` definido)
