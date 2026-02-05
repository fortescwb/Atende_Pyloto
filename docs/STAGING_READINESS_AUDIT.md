# Auditoria de Prontidão para Staging — Atende_Pyloto

**Data:** 03 de fevereiro de 2026  
**Última atualização:** 03 de fevereiro de 2026  
**Objetivo:** Identificar e documentar o que precisa ser implementado para deploy em staging com credenciais reais (WhatsApp, OpenAI) no Google Cloud, usando Upstash (Redis) e Cloud Tasks para filas.

---

## 🚀 Deploy em Staging — CONCLUÍDO

**Realizado em:** 03 de fevereiro de 2026

### Infraestrutura Provisionada

| Recurso                   | Configuração                                                    |
|---------------------------|-----------------------------------------------------------------|
| **Projeto GCP**           | `atende-pyloto` (ID: 691572891105)                              |
| **Região**                | `us-central1`                                                   |
| **Artifact Registry**     | `us-central1-docker.pkg.dev/atende-pyloto/atende`               |
| **Cloud Run Service**     | `atende-pyloto-staging`                                         |
| **URL do Serviço**        | https://atende-pyloto-staging-691572891105.us-central1.run.app  |

### Secrets no Secret Manager

- `openai-api-key-staging`
- `redis-url-staging`
- `whatsapp-access-token-staging`
- `whatsapp-api-version-staging`
- `whatsapp-business-account-id-staging`
- `whatsapp-phone-number-id-staging`
- `whatsapp-verify-token-staging`
- `whatsapp-webhook-secret-staging`

### Validação dos Endpoints

```bash
# Health Check — OK ✅
curl https://atende-pyloto-staging-691572891105.us-central1.run.app/health
# {"status":"healthy","service":"atende-pyloto","timestamp":"...","version":"1.0.0"}

# Webhook Verification — OK ✅
curl "https://atende-pyloto-staging-691572891105.us-central1.run.app/webhook/whatsapp/?hub.mode=subscribe&hub.verify_token=Pyloto_da_cadeia_ALIMENTAR&hub.challenge=test123"
# test123
```

### Próximos Passos

1. ✅ **Configurar webhook no Meta Developer Portal** apontando para a URL do serviço
2. ✅ **Implementar Stores** (Redis/Firestore) para sessão e dedupe — CONCLUÍDO
3. ✅ **Implementar integração com Secret Manager** no código — CONCLUÍDO
4. ⚠️ **Aumentar cobertura de testes** para 80%+ (atual: 50%)
5. 🔄 **Testar fluxo completo** com mensagens reais do WhatsApp

---

## Resumo Executivo

O repositório **Atende_Pyloto** já opera na **arquitetura Otto (agente único + utilitários)**; menções ao pipeline de 4 agentes a seguir são históricas. FSM e camadas continuam bem definidas. Os componentes críticos de infraestrutura para build e deploy foram implementados:

|                    Categoria                    |         Estado                      |  Bloqueador para Staging?  |
|-------------------------------------------------|-------------------------------------|----------------------------|
|              Arquitetura e código               |   ✅ 95% pronto                     |   Não                      |
|             Pipeline IA (Otto + utilitários)    |   ✅ Implementado                   |   Não                      |
|                       FSM                       |   ✅ Implementado                   |   Não                      |
|           **Aplicação ASGI (FastAPI)**          |   ✅ Implementado                   |   Não                      |
|            **Rotas HTTP (webhooks)**            |   ✅ Implementado                   |   Não                      |
|                 **Dockerfile**                  |   ✅ Implementado                   |   Não                      |
|               **cloudbuild.yaml**               |   ✅ Implementado                   |   Não                      |
|      **requirements.txt / pyproject.toml**      |   ✅ Implementado                   |   Não                      |
|  **Implementações de Stores (Redis/Firestore)** |   ✅ Implementado                   |   Não                      |
|          **Secret Manager integration**         |   ✅ Implementado                   |   Não                      |
|              Variáveis de ambiente              |   ⚠️ Settings definidos, .env vazio |   SIM                      |
|               Cobertura de testes               |   ⚠️ 55% (meta 80%)                 |   Não bloqueia staging     |

---

## 1) Achados por Severidade

### 1.1 CRÍTICO — Bloqueadores para Staging

#### ✅ C1: Aplicação ASGI — IMPLEMENTADO

**Situação anterior:** Apenas TODO, sem FastAPI.

**Implementação realizada:**

- FastAPI configurado em [src/app/app.py](src/app/app.py)
- Rotas organizadas em [src/api/routes/](src/api/routes/):
  - `GET /health` — Health check
  - `GET /ready` — Readiness probe
  - `GET /webhook/whatsapp` — Verificação de webhook (challenge)
  - `POST /webhook/whatsapp` — Recebimento de eventos

**Estrutura criada:**

```tree
src/api/routes/
├── __init__.py          # Exports create_api_router
├── router.py            # Agregador de rotas
├── health/
│   ├── __init__.py
│   └── router.py        # /health e /ready
└── whatsapp/
    ├── __init__.py
    ├── router.py        # Router do canal
    └── webhook.py       # GET/POST webhook
```

---

#### ✅ C2: Dockerfile — IMPLEMENTADO

**Situação anterior:** Nenhum Dockerfile encontrado no repositório.

**Implementação realizada (03/02/2026):**

- Arquivo [Dockerfile](Dockerfile) criado com:
  - Base `python:3.12-slim` otimizada
  - `dumb-init` para signal handling correto em containers
  - Usuário não-root para segurança
  - Health check configurado
  - Workers configuráveis via `UVICORN_WORKERS`
  - Suporte a `PORT` dinâmica (Cloud Run)

---

#### ✅ C3: pyproject.toml — IMPLEMENTADO

**Situação anterior:** Nenhum arquivo de dependências encontrado.

**Implementação realizada (03/02/2026):**

- Arquivo [pyproject.toml](pyproject.toml) criado com:
  - Todas as dependências de produção (FastAPI, Pydantic, Google Cloud, Redis, OpenAI, etc.)
  - Dependências de desenvolvimento opcionais (pytest, ruff, mypy)
  - Configuração de `ruff` para lint
  - Configuração de `pytest` com `asyncio_mode=auto`
  - Configuração de `mypy` para type checking
  - Configuração de `coverage`

---

#### ✅ C4: cloudbuild.yaml — IMPLEMENTADO

**Situação anterior:** Nenhum arquivo de CI/CD para Google Cloud Build.

**Implementação realizada (03/02/2026):**

- Arquivo [cloudbuild.yaml](cloudbuild.yaml) criado com:
  - Step 1: Lint check com ruff (fail-fast)
  - Step 2: Testes unitários com pytest (fail-fast)
  - Step 3: Build da imagem Docker
  - Step 4: Push para Artifact Registry (3 tags: SHA, latest, env)
  - Step 5: Deploy no Cloud Run com secrets do Secret Manager
  - Step 6: Smoke test no endpoint /health
  - Substitutions configuráveis para staging/production

---

#### ✅ C5: Implementações de Stores — IMPLEMENTADO

**Implementação realizada (04/02/2026):**

Stores de infraestrutura criados em [src/app/infra/stores/](src/app/infra/stores/):

1. **memory_stores.py** — Implementações em memória para dev/test:
   - `MemorySessionStore`, `MemoryDedupeStore`, `MemoryAuditStore`

2. **redis_session_store.py** — SessionStore com Upstash Redis:
   - SETEX com TTL, namespace `session:`

3. **redis_dedupe_store.py** — DedupeStore com SET NX atômico:
   - Namespace `dedupe:`, retorna True se duplicado

4. **firestore_audit_store.py** — AuditStore append-only:
   - Particionado por tenant/dia

**Bootstrap com DI:** [src/app/bootstrap/dependencies.py](src/app/bootstrap/dependencies.py)
**Testes:** 18 testes em [tests/app/infra/stores/](tests/app/infra/stores/)

---

#### ✅ C6: Secret Manager — IMPLEMENTADO

**Implementação realizada (04/02/2026):**

Integração em [src/app/infra/secrets/](src/app/infra/secrets/):

1. **gcp_secrets.py** — `GCPSecretProvider` com caching
2. **env_secrets.py** — `EnvSecretProvider` para dev local

Secrets configurados no GCP: `openai-api-key-staging`, `redis-url-staging`, etc.

---

#### ✅ C7: Rotas HTTP de webhook — IMPLEMENTADO

**Situação anterior:** Código de verificação e parsing existia, mas não havia rotas FastAPI.

**Implementação realizada:**
    - [src/api/routes/whatsapp/webhook.py](src/api/routes/whatsapp/webhook.py) — Rotas GET/POST
    - [src/api/routes/health/router.py](src/api/routes/health/router.py) — /health e /ready

**Endpoints disponíveis:**
    - `GET /health` — Liveness probe
    - `GET /ready` — Readiness probe
    - `GET /webhook/whatsapp` — Verificação de webhook (Meta challenge)
    - `POST /webhook/whatsapp` — Recebimento de eventos inbound

---

### 1.2 ALTO — Necessário antes de testes reais

#### ⚠️ A1: .env vazio

**Evidência:** Arquivo `.env` existe mas está vazio.

**Variáveis obrigatórias para staging:**

```env
# Ambiente
ENVIRONMENT=staging
GCP_PROJECT=seu-projeto-gcp
SERVICE_NAME=atende-pyloto

# WhatsApp (Graph API)
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_BUSINESS_ACCOUNT_ID=...
WHATSAPP_ACCESS_TOKEN=secret:whatsapp-access-token
WHATSAPP_VERIFY_TOKEN=secret:whatsapp-verify-token
WHATSAPP_WEBHOOK_SECRET=secret:whatsapp-webhook-secret

# OpenAI
OPENAI_API_KEY=secret:openai-api-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_ENABLED=true

# Redis (Upstash)
REDIS_URL=secret:redis-url
SESSION_STORE_BACKEND=redis
DEDUPE_BACKEND=redis

# Cloud Tasks
QUEUE_BACKEND=cloud_tasks
CLOUD_TASKS_PROJECT_ID=seu-projeto-gcp
CLOUD_TASKS_LOCATION=us-central1

# Firestore
FIRESTORE_PROJECT_ID=seu-projeto-gcp
```

---

#### ⚠️ A2: Cloud Tasks client não implementado

**Evidência:** Settings existem em [src/config/settings/infra/cloud_tasks.py](src/config/settings/infra/cloud_tasks.py), mas não há implementação de client.

**Implementação necessária:**

```python
# src/app/infra/queue/cloud_tasks_client.py
from google.cloud import tasks_v2

class CloudTasksClient:
    async def enqueue(self, queue_name: str, payload: dict, delay_seconds: int = 0) -> str:
        """Enfileira tarefa no Cloud Tasks."""
```

---

#### ⚠️ A3: Bootstrap não conecta implementações concretas

**Evidência:** [`src/app/bootstrap/__init__.py`](src/app/bootstrap/__init__.py) **apenas configura logging.**

**Implementação necessária:**
    - Factory para criar stores baseado em settings
    - Injeção de dependências no use case
    - Wiring de adapters concretos

---

### 1.3 MÉDIO — Qualidade e robustez

#### ⚠️ M1: Cobertura de testes 55% (meta 80%)

**Situação:** 395 testes, cobertura geral 55%.

**Módulos sem cobertura:**
    - `config/settings/` — 0%
    - `app/coordinators/` — 0%
    - `app/bootstrap/` — parcial

---

#### ⚠️ M2: .gitignore vazio

**Evidência:** Arquivo existe mas está vazio.

**Conteúdo necessário:**

```gitignore
# Python
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
*.egg-info/
dist/
build/

# Env
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/

# Secrets
*.pem
*.key
secrets/
```

---

## 2) Impacto e Riscos

|        Gap         |       Impacto         |            Risco                    |
|--------------------|-----------------------|-------------------------------------|
| Sem FastAPI        | Não recebe webhooks   | **Bloqueador total**                |
| Sem Dockerfile     | Não faz deploy        | **Bloqueador total**                |
| Sem requirements   | Build falha           | **Bloqueador total**                |
| Sem stores Redis   | Sem sessões/dedupe    | Funciona com memory (dev only)      |
| Sem Secret Manager | Secrets expostos      | Risco de segurança                  |
| Sem Cloud Tasks    | Sem filas assíncronas | Processamento síncrono (mais lento) |

---

## 3) Recomendações Priorizadas

### Fase 1: Infraestrutura Básica (Bloqueadores)

1. **Criar requirements.txt** com todas as dependências
2. **Criar Dockerfile** para Cloud Run
3. **Implementar FastAPI app** com rotas de webhook
4. **Criar cloudbuild.yaml** para CI/CD

### Fase 2: Stores e Persistência

5.**Implementar RedisSessionStore** (Upstash)
6.**Implementar RedisDedupeStore** (Upstash)
7.**Implementar FirestoreAuditStore**
8.**Integrar Secret Manager** para carregar secrets

### Fase 3: Filas e Assincronismo

9.**Implementar CloudTasksClient**
10.**Criar worker para processamento assíncrono**

### Fase 4: Refinamentos

11.**Expandir cobertura de testes** para 80%
12.**Configurar .gitignore** adequadamente
13.**Documentar variáveis de ambiente** (.env.example)

---

## 4) Checklist de Validação para Staging

### Pré-requisitos de Infraestrutura

- [ ] Dockerfile criado e testado localmente
- [ ] requirements.txt com todas as dependências
- [ ] cloudbuild.yaml configurado
- [ ] Projeto GCP configurado com APIs habilitadas:
  - Cloud Run
  - Cloud Build
  - Cloud Tasks
  - Firestore
  - Secret Manager
  - Cloud Storage

### Secrets no Secret Manager

- [ ] `openai-api-key` — Chave da API OpenAI
- [ ] `whatsapp-access-token` — Token de acesso Graph API
- [ ] `whatsapp-verify-token` — Token de verificação de webhook
- [ ] `whatsapp-webhook-secret` — Secret para validação HMAC
- [ ] `redis-url` — URL do Upstash Redis

### Configuração WhatsApp Business

- [ ] App registrado no Meta for Developers
- [ ] Webhook URL configurado: `https://<cloud-run-url>/webhook/whatsapp`
- [ ] Verify token configurado no Meta
- [ ] Phone number ID obtido
- [ ] Business Account ID obtido
- [ ] Permissões: `whatsapp_business_messaging`, `whatsapp_business_management`

### Configuração Upstash Redis

- [ ] Database criado
- [ ] URL de conexão obtida (com senha)
- [ ] Testado conexão

### Validações Pós-Deploy

- [ ] Health check responde 200 em `/health`
- [ ] Webhook verification funciona (GET retorna challenge)
- [ ] Webhook POST recebe e processa eventos
- [ ] Mensagem de teste enviada e respondida
- [ ] Logs estruturados visíveis no Cloud Logging
- [ ] Sessões persistidas no Redis
- [ ] Dedupe funcionando (mensagens duplicadas ignoradas)

---

## 5) Próximos Passos (Ordem de Execução)

| #  |     Tarefa                     | Estimativa | Dependência |
|----|--------------------------------|------------|-------------|
| 1  | Criar requirements.txt         | 30min      | —           |
| 2  | Criar Dockerfile               | 30min      | 1           |
| 3  | Implementar FastAPI com rotas  | 2-3h       | —           |
| 4  | Implementar RedisSessionStore  | 1-2h       | —           |
| 5  | Implementar RedisDedupeStore   | 1h         | 4           |
| 6  | Integrar Secret Manager        | 1-2h       | —           |
| 7  | Atualizar bootstrap com DI     | 1-2h       | 4, 5, 6     |
| 8  | Criar cloudbuild.yaml          | 1h         | 1, 2        |
| 9  | Testar localmente com Docker   | 1h         | 2, 3        |
| 10 | Deploy em staging              | 1h         | 8, 9        |
| 11 | Configurar webhook no Meta     | 30min      | 10          |
| 12 | Testes end-to-end              | 2h         | 11          |

**Estimativa total:** 12-16 horas de desenvolvimento

---

## 6) Arquivos a Criar

```tree
Atende_Pyloto/
├── Dockerfile                          # CRIAR
├── requirements.txt                    # CRIAR
├── cloudbuild.yaml                     # CRIAR
├── .env.example                        # CRIAR
├── .gitignore                          # ATUALIZAR
└── src/
    ├── app/
    │   ├── app.py                      # MODIFICAR (adicionar FastAPI)
    │   ├── routes/                     # CRIAR
    │   │   ├── __init__.py
    │   │   ├── health.py               # /health, /ready
    │   │   └── webhooks.py             # /webhook/whatsapp
    │   ├── infra/
    │   │   ├── stores/                 # CRIAR
    │   │   │   ├── __init__.py
    │   │   │   ├── redis_session.py
    │   │   │   ├── redis_dedupe.py
    │   │   │   └── firestore_audit.py
    │   │   ├── queue/                  # CRIAR
    │   │   │   ├── __init__.py
    │   │   │   └── cloud_tasks.py
    │   │   └── secrets/                # CRIAR
    │   │       ├── __init__.py
    │   │       └── gcp_secrets.py
    │   └── bootstrap/
    │       ├── __init__.py             # MODIFICAR (adicionar DI)
    │       └── dependencies.py         # CRIAR (factory de stores)
    └── config/
        └── settings/
            └── secrets.py              # CRIAR (integração Secret Manager)
```

---

## Conclusão

O Atende_Pyloto possui **base sólida de arquitetura e lógica de negócio**, mas **falta toda a camada de runtime e infraestrutura** necessária para deploy. Os componentes de IA (Otto + utilitários), FSM e validação estão bem implementados e testados.

**Prioridade absoluta:** Criar a aplicação FastAPI, Dockerfile e implementações de stores para viabilizar o primeiro deploy em staging.
