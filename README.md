# README antes de qualquer alteração implantação de código

Esse arquivo explica o que deverá existir em cada pasta dentro de `Atende_Pyloto/src`
Esse repositório esta em início de desenvolvimento, nenhum teste ou uso real foi feito.

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

Subpastas: - `ai/config/`: configuração e contratos de IA (modelos, thresholds, timeouts). - `ai/core/`: core de execução/orquestração interna de IA (interfaces e pipeline interno de IA). - `ai/models/`: modelos/DTOs para IA (entradas/saídas). - `ai/prompts/`: prompts versionados: - `base_prompts/`: peças reutilizáveis (system/base templates). - `state_prompts/`: prompts de seleção de estado/fluxo. - `validation_prompts/`: prompts de validação/guardrails. - `ai/rules/`: regras determinísticas que não dependem de LLM. - `ai/services/`: serviços de alto nível (ex.: classificar intenção, gerar opções). - `ai/utils/`: helpers de IA (parsers, normalizadores de output, etc.).

### 2.2 `src/api/` — Interface/Edge (entrada e saída do mundo externo)

**Escopo:** camada de borda e adapters de canais.  
**Responsabilidade:** receber requests, validar assinatura, normalizar payload, construir payloads, aplicar limites/validações de API.

Subpastas: - `api/connectors/`: conectores por canal. - `api/connectors/whatsapp/`: - `webhook/`: receive/verify/signature. - `inbound/`: entrada processável (event_id, handler, normalize). - `outbound/`: estruturas/rotinas outbound (quando existirem). - `outbound_flow/`: fluxo de envio (client e coordenação). - módulos locais (`http_client.py`, `signature.py`, `message_builder.py`, etc.) devem ser SRP e pequenos. - `api/normalizers/`: normalizadores por fornecedor/protocolo (ex.: `graph_api/`, `linkedin`, `google` e outros). - `api/payload_builders/`: builders por destino (apple/google/graph_api/linkedin/tiktok). - `api/validators/`: validações por canal/protocolo (ex.: `validators/graphapi/`).

**Não pode:** conter decisão de FSM, regras de sessão, policies globais, ou orquestração de casos de uso. Isso é `app/` e `fsm/`.

### 2.3 `src/app/` — Aplicação (orquestração, casos de uso e infraestrutura interna)

**Escopo:** “coração” do sistema: coordena regras, FSM, IA e infraestrutura.  
**Padrão mental:** `app` executa; `api` adapta; `ai` decide; `fsm` governa; `utils` apoia.

Subpastas: - `app/bootstrap/`: composition root (factories, inicialização, wiring). - `app/coordinators/`: fluxos end‑to‑end (inbound → pipeline → outbound). - `app/use_cases/`: casos de uso (inputs/outputs, sem IO direto). - `app/services/`: serviços de aplicação (unidades reutilizáveis de orquestração). - `app/infra/`: implementações concretas de IO internas (stores, filas, http, redis, firestore, secrets). - `app/protocols/`: contratos/interfaces que o app exige (store, queue, http, etc.). - `app/sessions/`: modelos e componentes de sessão (regras de idempotência e persistência via protocolos). - `app/policies/`: políticas (rate limit, abuse detection, dedupe/TTL/retry). - `app/observability/`: logs estruturados, tracing/correlation, métricas. - `app/constants/`: constantes da aplicação (não específicas de canal).

### 2.4 `src/config/` — Configuração e settings

**Escopo:** settings tipados, carregamento de env, defaults, validação de config. - `config/settings/`: settings por canal/provedor e agregador. - `config/logging/`: logging config por canal/provedor e agregador.

### 2.5 `src/fsm/` — Máquina de estados (domínio determinístico)

**Escopo:** estados, transições e regras determinísticas. - `fsm/states/`: definições dos estados. - `fsm/transitions/`: transições permitidas. - `fsm/rules/`: regras de transição. - `fsm/manager/`: aplicação/validação da FSM.

### 2.6 `src/utils/` — Utilitários comuns (cross‑cutting)

**Escopo:** helpers genéricos (sem regra de negócio). - `utils/errors/`: exceções tipadas - `utils/ids.py`: IDs/fingerprints - `utils/audit.py`: helpers de auditoria (sem PII) - `utils/timing.py`: medições/latências - demais arquivos somente se forem realmente transversais

## Funcionamento

┌─────────────────────────────────────────────────────────────────┐
│ ProcessInboundCanonicalUseCase │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        AIOrchestrator                           │
│              (coordena 4 agentes em sequência)                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
       ┌───────────────────────┼──────────────────────────┐
       │                       │                          │
       ▼                       ▼                          ▼
┌───────────────┐ ┌───────────────────┐ ┌─────────────────┐
│   StateAgent  │ │     ResponseAgent │ │ MessageTypeAgent│
│   (LLM #1)    │ │       (LLM #2)    │ │    (LLM #3)     │
│               │ │                   │ │                 │
│ - prev_state  │ │ - 2-3 candidatos  │ │ - tipo sugerido │
│ - curr_state  │ │ - confidence cada │ │ - parâmetros    │
│ - next_states │ │ - tom/estilo      │ │ - confidence    │
└───────┬───────┘ └─────────┬─────────┘ └────────┬────────┘
        │                   │                    │
        └───────────────────┼────────────────────┘
                            │
                            ▼
                 ┌───────────────────────┐
                 │ DecisionAgent         │
                 │ (LLM #4)              │
                 │                       │
                 │ - consolida 3 outputs │
                 │ - escolhe resposta    │
                 │ - escolhe estado      │
                 │ - aplica threshold    │
                 │ - confidence final    │
                 └───────────┬───────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │ MasterDecision        │
                 │ - final_text          │
                 │ - final_state         │
                 │ - final_message_type  │
                 │ - understood: bool    │
                 │ - confidence: float   │
                 └───────────────────────┘
**Os tipos de mensagens que a IA pode sugerir para a resposta, devem ser os mesmos disponíveis para o canal whatsapp**

Para cada agente deve existir um arquivo de configuração em formato yaml ou outro mais lógico, assim, poderemos versionar os agentes, dar contexto e torna-los mais assertivos

**A estrutura e criação de arquivos deve serguir as [REGAS_E_PADROES.md] bem como o padrão adotado no repositório. IA dentro da pasta IA, config em config, etc, etc.**

Próximos Passos (Priorizados)
[CRÍTICO] Criar contratos para StateAgentResult e DecisionAgentResult
[CRÍTICO] Atualizar AIClientProtocol com novos métodos
[ALTO] Implementar prompts para os 4 agentes
[ALTO] Refatorar AIOrchestrator para 4 pontos
[MÉDIO] Modificar ResponseGenerationResult para candidatos
[MÉDIO] Adicionar threshold de confiança
[BAIXO] Adicionar tipo reaction em MessageType
[BAIXO] Implementar paralelização de agentes 1-3

Paralelização: Os agentes 1, 2, 3 podem rodar em paralelo.

Threshold: O valor de confiança mínimo para aceitar a decisão é 0.7.

Fallback: O texto a ser usado quando confidence < threshold é "Desculpe, não entendi. Pode reformular?".

1 LLM deverá escolher 1 entre os seguintes tipos de mensagem: text, interactive_button, interactive_list, template, ou reaction (Reaction servirá apenas quando nenhuma mensagem é necessária, apenas uma reação, por exemplo, usuário finalizou dizendo "blz, obg", aqui podemos apenas reagir a resposta do usuário)
2 Estados FSM são fixos. Usar os 10 existentes.
3 Path dos YAMLs de configuração é config/agents/{agent_name}.yaml
4 3 candidatos de resposta, um formal, um casual e um empático.
6 Baixa confiança → escalar após quantas vezes? 3 vezes consecutivas
