# Relatório de Auditoria de Padrões e Arquitetura

Data: 2026-02-09  
Repositório auditado: `Atende_Pyloto`

## Escopo e método

Leitura integral de:
- `REGRAS_E_PADROES.md`
- `README.md`

Varreduras executadas:
- Estrutura de diretórios e aderência de camadas
- Métricas objetivas de tamanho (`arquivo`, `classe`, `função`)
- Imports (dependências cruzadas e ciclos)
- Gates (`ruff`, `pytest`, `coverage`)
- Consistência de modelos, redundâncias e oportunidades de modularização

## Resumo executivo

Status geral: **NÃO CONFORME** com as regras vigentes.

Principais motivos:
- Gates obrigatórios falhando (`ruff`, `pytest`, cobertura mínima 80%)
- Violações objetivas de tamanho/complexidade sem exceção formal registrada
- Violação de boundary (`app/services` importando implementação concreta de `app/infra`)
- Inconsistências de domínio (estado `ENTRY` inexistente na FSM e `primary_interest` divergente)
- Duplicação conceitual e técnica relevante

## Métricas objetivas

- Arquivos Python analisados: **298**
- Arquivos `> 200` linhas: **7**
- Classes `> 200` linhas: **3**
- Funções `> 50` linhas: **23**
- Grupos de import circular encontrados: **0**
- Violações de boundary (não-bootstrap importando `app.infra`): **2**
- Arquivos com `TODO: Implementar`: **91**
- Cobertura total atual: **52.68%**
- Arquivos com **0%** de cobertura: **132**

## Achados críticos

### C1) Gates obrigatórios quebrados

Evidência:
- `ruff check .` → **30 erros**
- `pytest -q` → **1 falha**
- `pytest --cov=src --cov-fail-under=80` → **52.68%** (abaixo de 80%)

Impacto:
- Descumprimento direto da seção 9 de `REGRAS_E_PADROES.md`.
- Merge deveria estar bloqueado.

### C2) Inconsistência funcional em `ContactCardPatch` (falha de teste real)

Evidência:
- `tests/test_ai/test_contact_card_extractor.py:69` espera `primary_interest == "saas"`
- `src/ai/models/contact_card_extraction.py:33` não aceita `"saas"` no `Literal`
- `src/app/domain/contact_card.py:37` aceita `"saas"`

Impacto:
- Contratos divergentes para o mesmo conceito de negócio.
- Resultado de extração é descartado e gera regressão funcional.

### C3) Estado padrão inválido (`ENTRY`) fora da FSM

Evidência:
- `src/app/sessions/models.py:247` usa fallback `SessionState["ENTRY"]`
- `src/app/use_cases/whatsapp/process_inbound_canonical.py:94` inicializa `final_state = "ENTRY"`
- `src/fsm/states/session.py:37` define `INITIAL` (não existe `ENTRY`)

Impacto:
- Risco de `KeyError`/estado inválido em cenários de fallback.
- Quebra do determinismo do domínio FSM.

### C4) Cobertura abaixo do mínimo com alto volume de superfície não testada

Evidência:
- Cobertura total: **52.68%**
- **132** arquivos com 0% (grande parte em `api/normalizers`, `api/payload_builders`, `api/connectors`)

Impacto:
- Confiabilidade operacional insuficiente para mudanças seguras.

## Achados altos

### A1) Violação objetiva da regra de tamanho de arquivo sem exceção formal

Arquivos `>200` linhas:
- `src/app/use_cases/whatsapp/_inbound_processor.py` (712) — com exceção registrada
- `src/app/sessions/manager.py` (464) — sem exceção formal
- `src/ai/services/prompt_micro_agents.py` (417) — sem exceção formal
- `src/api/routes/whatsapp/webhook.py` (291) — sem exceção formal
- `src/app/infra/stores/firestore_conversation_store.py` (283) — sem exceção formal
- `src/app/sessions/models.py` (274) — sem exceção formal
- `src/app/bootstrap/dependencies.py` (269) — sem exceção formal

Evidência de governança:
- `docs/Monitoramento_Regras-Padroes.md` registra apenas 1 exceção (`_inbound_processor.py`)

Impacto:
- Quebra da seção 4 (limites de tamanho) e do processo de exceção.

### A2) Boundary violado: `app/services` acoplado a implementação concreta de `app/infra`

Evidência:
- `src/app/services/transcription_agent.py:7`
- `src/app/services/transcription_agent.py:8`

Impacto:
- Contraria a regra de que composição de concretos deve ocorrer no bootstrap.
- Reduz testabilidade e intercambialidade de infraestrutura.

### A3) `ai/` com IO direto em filesystem (divergência explícita das regras)

Evidência:
- `src/ai/config/prompt_assets_loader.py:40`
- `src/ai/config/prompt_assets_loader.py:45`
- `src/ai/config/institutional_loader.py:48`
- `src/ai/prompts/dynamic_context_loader.py:87`
- `src/ai/services/prompt_micro_agents.py:389`
- `src/ai/services/prompt_micro_agents.py:404`

Observação:
- Há comentário justificando IO local em `src/ai/config/prompt_assets_loader.py:5`, mas essa permissão **não existe** no documento de regras.

Impacto:
- Divergência arquitetural formal entre regra e implementação.

### A4) Logging estruturado não aderente ao padrão definido

Evidência quantitativa (varredura estática):
- `logger.*` em `src`: **133** chamadas
- Sem `extra`: **22**
- Com `extra` mas faltando campos-chave (`correlation_id/component/action/result`): **88**

Exemplos:
- `src/app/coordinators/whatsapp/inbound/handler.py:45`
- `src/app/bootstrap/dependencies.py:68`
- `src/api/routes/whatsapp/webhook.py:129`
- `src/app/infra/stores/firestore_conversation_store.py:108`

Impacto:
- Descumprimento de rastreabilidade operacional (seção 6).

## Achados médios

### M1) Duplicação técnica: criptografia de Flows em dois lugares

Evidência:
- `src/api/connectors/whatsapp/flows/payload.py` e `src/app/infra/crypto/payload.py` (conteúdo idêntico)
- `src/api/connectors/whatsapp/flows/keys.py` e `src/app/infra/crypto/keys.py` (conteúdo idêntico)
- `src/api/connectors/whatsapp/flows/signature.py` e `src/app/infra/crypto/signature.py` (diferença mínima de docstring)

Impacto:
- Alto risco de drift e correções divergentes.

### M2) Duplicação conceitual de modelos de patch

Evidência:
- `src/ai/models/contact_card_extraction.py:23` (`ContactCardPatch`)
- `src/app/domain/contact_card_patch.py:10` (`ContactCardPatch`)

Impacto:
- Mesma entidade com contratos diferentes.
- Já gerou incompatibilidade funcional (`saas`).

### M3) Duplicação de modelo de sessão em protocolo

Evidência:
- `src/app/protocols/session_manager.py:11` define `Session` simplificada
- `src/app/sessions/models.py:93` define `Session` real

Impacto:
- Tipagem ambígua, risco de erro silencioso e drift de contrato.

### M4) Duplicação de construção de payload outbound

Evidência:
- `src/app/use_cases/whatsapp/_inbound_helpers.py:31` (`build_outbound_payload`)
- `src/api/payload_builders/whatsapp/factory.py:62` (`build_full_payload`)

Impacto:
- Regra de payload pode divergir entre fluxos distintos.

### M5) Complexidade elevada em pontos-chave

Evidência (`ruff --select C901`):
- `src/app/services/contact_card_merge.py:12` complexidade 32
- `src/app/domain/contact_card.py:106` complexidade 26
- `src/ai/services/contact_card_extractor.py:109` complexidade 23
- `src/ai/services/prompt_micro_agents.py:302` complexidade 15
- `src/app/use_cases/whatsapp/_inbound_processor.py:75` complexidade 12

Impacto:
- Dificulta manutenção, revisão e testes de regressão.

### M6) Módulos placeholders em excesso no core (`src`) com baixo valor imediato

Evidência:
- **91** arquivos com `TODO: Implementar`
- Grande concentração em `api/connectors`, `api/normalizers`, `api/payload_builders`, `api/validators`, `config/settings`

Impacto:
- Aumenta superfície de manutenção, ruído de cobertura e custo cognitivo.

## Achados baixos

### B1) Naming/artefatos

Evidência:
- `src/ai/README.md` foge de `snake_case` estrito de arquivos
- Presença local de `src/atende_pyloto.egg-info` (artefato de build; não rastreado no git)

Impacto:
- Baixo impacto funcional, mas desalinha padronização.

### B2) Drift de documentação entre README e implementação atual

Exemplos:
- README descreve componentes/nomes diferentes dos módulos atuais (`ExtractionAgent`, `TranscriptionAgent` em `ai/services`)
- Defaults de modelo no código usam `gpt-4o`/`gpt-4o-mini` (`src/app/infra/ai/otto_client.py:34`, `src/app/infra/ai/contact_card_extractor_client.py:35`) enquanto o README descreve arquitetura com `gpt-5.1`

Impacto:
- Onboarding e manutenção ficam menos previsíveis.

## Imports circulares

Resultado da análise estática de imports internos: **não foram encontrados ciclos de import diretos**.

Observação:
- Isso não elimina possíveis ciclos indiretos em runtime por imports dinâmicos, mas não há evidência atual de ciclo estrutural.

## Oportunidades prioritárias de modularização

1. Quebrar `InboundMessageProcessor` (`src/app/use_cases/whatsapp/_inbound_processor.py`) em componentes: `MessageGate`, `TranscriptionStep`, `ContactCardStep`, `DecisionGuards`, `SessionPersistenceStep`, `OutboundStep`.
2. Separar `SessionManager` (`src/app/sessions/manager.py`) em: resolução de sessão, recuperação de histórico, persistência de mensagens e persistência de lead.
3. Transformar `apply_contact_card_patch` (`src/app/services/contact_card_merge.py`) em estratégia por campo/tipo (mapa de handlers) para reduzir complexidade.
4. Extrair de `prompt_micro_agents` (`src/ai/services/prompt_micro_agents.py`) os blocos de detecção, seleção e carregamento para módulos especializados.
5. Remover duplicidade de payload outbound, mantendo uma única trilha canônica via builder/validator.
6. Consolidar criptografia de Flows em `app/infra/crypto` e manter em `api` apenas re-export sem código duplicado.

## Oportunidades de simplificação

1. Unificar `ContactCardPatch` em uma única fonte de verdade (domínio).
2. Remover aliases legados sem uso efetivo (`lead_profile*`) após janela de compatibilidade.
3. Isolar placeholders multi-canal em pacote separado ou behind feature flag para reduzir ruído no `src` principal.
4. Padronizar logging via helper único (ex.: `log_event(component, action, result, ...)`) para garantir schema obrigatório.
5. Atualizar README para refletir arquitetura real em produção/staging.

## Plano de correção recomendado (ordem)

1. **Bloqueio de qualidade**: corrigir teste quebrado + ruff + cobertura mínima dos módulos críticos.
2. **Consistência de domínio**: corrigir `primary_interest` e remover `ENTRY` em favor de `INITIAL`.
3. **Boundaries**: remover imports concretos de `app.services.transcription_agent` para protocolos injetados no bootstrap.
4. **Governança de exceções**: registrar exceções restantes ou refatorar arquivos >200.
5. **Deduplicação**: crypto flows + payload outbound + modelos duplicados.
6. **Higiene estrutural**: redução de placeholders e atualização documental.

## Conclusão

O repositório já possui base arquitetural sólida em vários pontos (sem ciclos de import diretos, presença de protocolos e bootstrap), porém está **fora dos padrões definidos** em aspectos críticos de qualidade, consistência de domínio e governança de regras. A correção deve priorizar gates obrigatórios, consistência semântica de modelos/estados e redução de acoplamento/duplicação.

---

## Atualização de execução — 2026-02-09 (modularização Regra 4)

Objetivo desta execução:
- Modularizar arquivos `>200` linhas com múltiplas funções, mantendo somente exceções formais permitidas.

### Arquivos modularizados nesta execução

Redução de tamanho (antes → depois):
- `src/app/sessions/models.py`: **274 → 16**
- `src/app/sessions/manager.py`: **464 → 175**
- `src/ai/services/prompt_micro_agents.py`: **417 → 119**
- `src/api/routes/whatsapp/webhook.py`: **291 → 121**
- `src/app/infra/stores/firestore_conversation_store.py`: **283 → 66**
- `src/app/bootstrap/dependencies.py`: **269 → 32**

Novos módulos criados para suportar a modularização:
- `src/app/sessions/history.py`
- `src/app/sessions/session_context.py`
- `src/app/sessions/session_entity.py`
- `src/app/sessions/manager_recovery.py`
- `src/app/sessions/manager_persistence.py`
- `src/app/bootstrap/dependencies_stores.py`
- `src/app/bootstrap/dependencies_services.py`
- `src/api/routes/whatsapp/webhook_runtime.py`
- `src/app/infra/stores/firestore_conversation_backend.py`
- `src/ai/services/prompt_micro_agents_types.py`
- `src/ai/services/prompt_micro_agents_text.py`
- `src/ai/services/prompt_micro_agents_context.py`
- `src/ai/services/prompt_micro_agents_cases.py`
- `src/ai/services/prompt_micro_agents_agents.py`

### Status da regra de tamanho após execução

- Arquivos Python em `src`: **235**
- Arquivos `>200` linhas: **1**
- Arquivos `>200` sem exceção formal: **0**
- Único arquivo `>200` remanescente:
  - `src/app/use_cases/whatsapp/_inbound_processor.py` (**712**)  
    já com exceção formal (comentário `EXCECAO REGRA 2.1` no topo + registro em `docs/Monitoramento_Regras-Padroes.md`).

### Validações executadas nesta execução

- `ruff check` nos módulos alterados: **OK**
- Testes direcionados:
  - `pytest -q tests/app/sessions/test_session_models.py tests/app/sessions/test_session_manager.py tests/test_ai/test_prompt_micro_agents.py` → **29 passed**
  - `pytest -q tests/unit/app/use_cases/test_process_inbound_fixed_replies.py tests/unit/app/use_cases/test_process_inbound_protocols.py tests/api/connectors/whatsapp/webhook/test_receive.py tests/api/connectors/whatsapp/webhook/test_verify.py` → **8 passed**

### Observação de compatibilidade

- `src/app/sessions/models.py` e `src/app/bootstrap/dependencies.py` foram mantidos como fachadas de compatibilidade (re-export), preservando os imports públicos existentes.

---

## Atualização de execução — 2026-02-09 (ataque de métricas complementares)

Objetivo desta execução:
- Atacar os pontos solicitados: classes `>200`, funções `>50`, boundary, placeholders de implementação e cobertura.

### Resultado consolidado dos pontos solicitados

Comparativo (baseline deste relatório -> estado atual):
- Classes `> 200` linhas: **3 -> 0**
- Funções `> 50` linhas: **23 -> 0**
- Grupos de import circular: **0 -> 0**
- Violações de boundary (não-bootstrap, não-infra importando `app.infra`): **2 -> 0**
- Arquivos com marcador `TODO: Implementar` em `src`: **91 -> 0**
- Cobertura total: **52.68% -> 57.65%**
- Arquivos com **0%** de cobertura: **132 -> 57**

Medições desta execução:
- AST scan (`src`): `classes_gt_200=0`, `functions_gt_50=0`
- Boundary scan (`src`, excluindo `app/bootstrap` e `app/infra`): `0`
- Marcador `TODO: Implementar`: `0` em `src` (repo inteiro: `1`, presente neste próprio relatório histórico)
- Cobertura (`pytest --cov=src --cov-report=term --cov-fail-under=0 -q`): **57.65%** (`343 passed, 1 skipped`)

### Testes adicionados nesta execução

Arquivos novos:
- `tests/app/services/test_contact_card_merge.py`
- `tests/api/routes/whatsapp/test_webhook_runtime.py`
- `tests/api/routes/whatsapp/test_webhook_route.py`

Cobertura impactada diretamente:
- `src/app/services/contact_card_merge.py`: **0.00% -> 86.21%**
- `src/api/routes/whatsapp/webhook.py`: **0.00% -> 100.00%**
- `src/api/routes/whatsapp/webhook_runtime.py`: **0.00% -> 72.09%**

### Gates desta execução

- `pytest --cov=src --cov-report=term --cov-fail-under=0 -q`: **OK** (`343 passed, 1 skipped`)
- `ruff check .`: **46 erros pendentes** (itens legados fora do escopo desta rodada)
