# TODO Detalhado - Correções E2E Críticas

TODO baseado nas **falhas concretas** encontradas bem como lacunas estruturais identificadas

**Todo código mostrado aqui é apenas SUGESTÃO**
**Deve ser implementado de acordo com o que for mais lógico**
**Esse documento deve ser mantido SEMPRE atualizado**

---

## ⚠️ BLOQUEADORES CRÍTICOS (P0) - Impedem Deploy Seguro

### 1. **Race Condition Dedupe + Perda Silenciosa de Mensagens**

**Problema**:

```python
# src/app/use_cases/whatsapp/_inbound_processor.py:71-73
if await self._dedupe.is_duplicate(msg.message_id):
    return None
await self._dedupe.mark_processed(msg.message_id)
# ^ Marcado ANTES do pipeline completo
```

**Cenário de falha**:

1. Mensagem chega, passa por `is_duplicate()` → OK
2. `mark_processed()` marca como processada
3. Otto/Firestore falham
4. `webhook_runtime.py:63` engole exceção, retorna 200
5. **Mensagem perdida permanentemente**

**Correção obrigatória**:

```python
# src/app/use_cases/whatsapp/_inbound_processor.py

async def process(
    self,
    msg: NormalizedMessage,
    correlation_id: str,
    tenant_id: str,
) -> dict[str, Any] | None:
    # 1. Check dedupe (não marca ainda)
    if await self._dedupe.is_duplicate(msg.message_id):
        return None

    # 2. Marca como "em processamento" com TTL curto (30s)
    await self._dedupe.mark_processing(msg.message_id, ttl=30)

    try:
        # 3. Pipeline completo
        result = await self._execute_pipeline(msg, correlation_id, tenant_id)

        # 4. Sucesso: marca como processado permanentemente
        await self._dedupe.mark_processed(msg.message_id, ttl=86400)
        return result

    except Exception as exc:
        # 5. Falha: remove marca temporária para permitir retry
        await self._dedupe.unmark_processing(msg.message_id)
        raise  # Propaga exceção para webhook handler decidir
```

**Implementar em `redis_dedupe_store.py`**:

```python
# src/app/infra/stores/redis_dedupe_store.py

async def mark_processing(self, message_id: str, ttl: int = 30) -> None:
    """Marca mensagem como em processamento (TTL curto)."""
    key = f"processing:{self._key_prefix}:{message_id}"
    await self._client.setex(key, ttl, "1")

async def is_duplicate(self, message_id: str) -> bool:
    """Verifica se já processada OU em processamento."""
    processed_key = f"{self._key_prefix}:{message_id}"
    processing_key = f"processing:{self._key_prefix}:{message_id}"

    # Operação atômica com pipeline
    pipe = self._client.pipeline()
    pipe.exists(processed_key)
    pipe.exists(processing_key)
    results = await pipe.execute()

    return results[0] > 0 or results[1] > 0

async def unmark_processing(self, message_id: str) -> None:
    """Remove marca de processamento (em caso de falha)."""
    key = f"processing:{self._key_prefix}:{message_id}"
    await self._client.delete(key)
```

**Testes obrigatórios**:

```python
# tests/test_app/test_infra/test_redis_dedupe_store.py

async def test_dedupe_race_condition_handling():
    """Valida que mensagem não é perdida em falha após mark_processing."""
    store = RedisDedupe(...)
    msg_id = "test_race_123"

    await store.mark_processing(msg_id, ttl=5)
    assert await store.is_duplicate(msg_id) is True

    # Simula falha: desmarcar permite retry
    await store.unmark_processing(msg_id)
    assert await store.is_duplicate(msg_id) is False

async def test_dedupe_prevents_concurrent_processing():
    """Duas tasks não podem processar mesma mensagem simultaneamente."""
    store = RedisDedupe(...)
    msg_id = "test_concurrent_456"

    await store.mark_processing(msg_id)

    # Segunda tentativa deve detectar duplicata
    assert await store.is_duplicate(msg_id) is True
```

**Prazo**: 1 dia
**Arquivos afetados**:

- `src/app/use_cases/whatsapp/_inbound_processor.py`
- `src/app/infra/stores/redis_dedupe_store.py`
- `src/api/routes/whatsapp/webhook_runtime.py` (tratar exceções corretamente)

---

### 2. **Webhook Handler Não Propaga Erros Críticos**

**Problema**:

```python
# src/api/routes/whatsapp/webhook_runtime.py:63
except Exception as exc:
    logger.warning("inbound_processing_failed", ...)
    # ^ Engole exceção, retorna 200
```

**Correção**:

```python
# src/api/routes/whatsapp/webhook_runtime.py

async def _process_inbound_task(...):
    try:
        result = await process_inbound_use_case.execute(...)
        logger.info("inbound_processed", extra={...})

    except (RedisConnectionError, FirestoreUnavailableError) as exc:
        # Erros de infraestrutura: logar como ERROR e deixar task falhar
        logger.error(
            "inbound_infrastructure_failure",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
        )
        # NÃO envolve exceção - permite que task falhe e Meta faça retry
        raise

    except ValidationError as exc:
        # Erro de dados malformados: logar mas não retentar
        logger.warning("inbound_validation_failed", extra={...})
        # Mensagem inválida, não faz sentido retentar
        return

    except Exception as exc:
        # Erro desconhecido: logar e propagar
        logger.exception("inbound_unexpected_error", extra={...})
        raise
```

**Adicionar em `webhook.py`**:

```python
# src/api/routes/whatsapp/webhook.py:74

@router.post("/")
async def receive_webhook(...):
    try:
        background_tasks.add_task(...)
        return JSONResponse({"status": "received"}, status_code=200)

    except Exception as exc:
        # Se até o dispatch falhar, retornar 500 para Meta retentar
        logger.exception("webhook_dispatch_failed", ...)
        return JSONResponse(
            {"error": "internal_error", "message": "Failed to queue message"},
            status_code=500
        )
```

**Prazo**: 4 horas
**Arquivos afetados**:

- `src/api/routes/whatsapp/webhook_runtime.py`
- `src/api/routes/whatsapp/webhook.py`
- `src/utils/errors/exceptions.py` (adicionar `RedisConnectionError`, `FirestoreUnavailableError`)

---

### 3. **Readiness Check Falso Positivo**

**Problema**:

```python
# src/api/routes/health/router.py:68
# TODO: implementar checagem real de dependências
return JSONResponse({"status": "ready", "checks": {"app": "ok"}})
```

**Correção completa**:

```python
# src/api/routes/health/router.py

from dataclasses import dataclass
from typing import Literal

@dataclass
class HealthCheck:
    status: Literal["ok", "degraded", "failed"]
    latency_ms: float | None = None
    error: str | None = None

async def check_redis(redis_client) -> HealthCheck:
    """Testa conexão Redis com timeout."""
    try:
        start = time.perf_counter()
        await asyncio.wait_for(redis_client.ping(), timeout=2.0)
        latency = (time.perf_counter() - start) * 1000
        return HealthCheck(status="ok", latency_ms=latency)
    except asyncio.TimeoutError:
        return HealthCheck(status="failed", error="timeout")
    except Exception as exc:
        return HealthCheck(status="failed", error=type(exc).__name__)

async def check_firestore(firestore_client) -> HealthCheck:
    """Testa leitura rápida no Firestore."""
    try:
        start = time.perf_counter()
        # Lê documento de health check (criar na inicialização)
        doc = await asyncio.wait_for(
            firestore_client.collection("_health").document("check").get(),
            timeout=3.0
        )
        latency = (time.perf_counter() - start) * 1000
        return HealthCheck(status="ok" if doc.exists else "degraded", latency_ms=latency)
    except asyncio.TimeoutError:
        return HealthCheck(status="failed", error="timeout")
    except Exception as exc:
        return HealthCheck(status="failed", error=type(exc).__name__)

async def check_openai(openai_client) -> HealthCheck:
    """Testa API OpenAI com chamada leve."""
    try:
        start = time.perf_counter()
        # Listar modelos = chamada leve
        await asyncio.wait_for(openai_client.models.list(), timeout=5.0)
        latency = (time.perf_counter() - start) * 1000
        return HealthCheck(status="ok", latency_ms=latency)
    except asyncio.TimeoutError:
        return HealthCheck(status="degraded", error="timeout")  # Degraded, não failed
    except Exception as exc:
        return HealthCheck(status="degraded", error=type(exc).__name__)

@router.get("/ready")
async def readiness_probe(request: Request):
    """Readiness check com validação de dependências críticas."""
    checks = await asyncio.gather(
        check_redis(request.app.state.redis_client),
        check_firestore(request.app.state.firestore_client),
        check_openai(request.app.state.openai_client),
        return_exceptions=True
    )

    redis_check, firestore_check, openai_check = checks

    # Redis e Firestore são críticos
    critical_ok = (
        redis_check.status == "ok" and
        firestore_check.status == "ok"
    )

    # OpenAI pode estar degraded (usa fallback)
    openai_ok = openai_check.status in ("ok", "degraded")

    overall_status = "ready" if (critical_ok and openai_ok) else "not_ready"
    status_code = 200 if overall_status == "ready" else 503

    return JSONResponse(
        {
            "status": overall_status,
            "checks": {
                "redis": {"status": redis_check.status, "latency_ms": redis_check.latency_ms},
                "firestore": {"status": firestore_check.status, "latency_ms": firestore_check.latency_ms},
                "openai": {"status": openai_check.status, "latency_ms": openai_check.latency_ms},
            },
            "timestamp": datetime.utcnow().isoformat(),
        },
        status_code=status_code
    )
```

**Inicializar clients no bootstrap**:

```python
# src/app/bootstrap/__init__.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa clients
    app.state.redis_client = await create_redis_client()
    app.state.firestore_client = create_firestore_client()
    app.state.openai_client = create_openai_client()

    # Cria documento de health check no Firestore
    await app.state.firestore_client.collection("_health").document("check").set({
        "created_at": datetime.utcnow(),
        "purpose": "readiness_probe"
    })

    yield

    # Cleanup
    await app.state.redis_client.close()
```

**Prazo**: 1 dia
**Arquivos afetados**:

- `src/api/routes/health/router.py`
- `src/app/bootstrap/__init__.py`

---

### 4. **Validação de Configuração Não é Aplicada**

**Problema**:

```python
# src/config/settings/whatsapp.py:100 define validate()
# mas src/app/bootstrap/__init__.py:37 não chama

# Resultado: phone_number_id vazio só falha em runtime
```

**Correção**:

```python
# src/app/bootstrap/__init__.py

from config.settings.base.settings import Settings
from config.settings.whatsapp.api import WhatsAppSettings

def validate_all_settings():
    """Valida todas as configurações obrigatórias no startup."""
    errors = []

    # Valida WhatsApp
    try:
        wa_settings = WhatsAppSettings()
        wa_settings.validate()
    except ValueError as exc:
        errors.append(f"WhatsApp: {exc}")

    # Valida OpenAI
    try:
        from config.settings.ai.openai import OpenAISettings
        ai_settings = OpenAISettings()
        if not ai_settings.api_key:
            errors.append("OpenAI: OPENAI_API_KEY não configurado")
    except Exception as exc:
        errors.append(f"OpenAI: {exc}")

    # Valida Firestore
    try:
        from config.settings.infra.firestore import FirestoreSettings
        fs_settings = FirestoreSettings()
        if not fs_settings.project_id:
            errors.append("Firestore: FIRESTORE_PROJECT_ID não configurado")
    except Exception as exc:
        errors.append(f"Firestore: {exc}")

    if errors:
        error_msg = "\n".join(f"  - {e}" for e in errors)
        raise RuntimeError(f"Configuração inválida:\n{error_msg}")

    logger.info("settings_validated", extra={"component": "bootstrap"})

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Valida configurações ANTES de qualquer inicialização
    validate_all_settings()

    configure_logging()
    # ... resto do bootstrap
```

**Adicionar em `config/settings/whatsapp/api.py`**:

```python
def validate(self) -> None:
    """Valida configuração obrigatória."""
    errors = []

    if not self.phone_number_id:
        errors.append("WHATSAPP_PHONE_NUMBER_ID não configurado")

    if not self.access_token:
        errors.append("WHATSAPP_ACCESS_TOKEN não configurado")

    if not self.verify_token:
        errors.append("WHATSAPP_VERIFY_TOKEN não configurado")

    if errors:
        raise ValueError("; ".join(errors))
```

**Prazo**: 4 horas
**Arquivos afetados**:

- `src/app/bootstrap/__init__.py`
- `src/config/settings/whatsapp/api.py`
- `src/config/settings/ai/openai.py` (adicionar validação)

---

### 5. **Processamento Async Sem Durabilidade**

**Problema**:

```python
# src/api/routes/whatsapp/webhook_runtime.py:129
asyncio.create_task(_process_inbound_task(...))
# ^ Tarefa em memória, perdida em restart/crash
```

**Solução pragmática para MVP** (sem adicionar infra de fila agora):

```python
# src/api/routes/whatsapp/webhook_runtime.py

# Adicionar limite de tasks concorrentes
_TASK_SEMAPHORE = asyncio.Semaphore(100)  # Máx 100 tasks simultâneas
_ACTIVE_TASKS: set[asyncio.Task] = set()

async def _process_with_tracking(
    process_inbound_use_case,
    payload,
    correlation_id,
    tenant_id,
):
    """Wrapper que rastreia task ativa."""
    async with _TASK_SEMAPHORE:
        try:
            await _process_inbound_task(
                process_inbound_use_case,
                payload,
                correlation_id,
                tenant_id
            )
        finally:
            # Remove da lista de tasks ativas
            pass

def dispatch_processing(...):
    """Despacha com limite e tracking."""
    task = asyncio.create_task(
        _process_with_tracking(...)
    )
    _ACTIVE_TASKS.add(task)
    task.add_done_callback(_ACTIVE_TASKS.discard)

    logger.info(
        "task_dispatched",
        extra={
            "correlation_id": correlation_id,
            "active_tasks": len(_ACTIVE_TASKS),
        }
    )

# No lifespan shutdown
async def shutdown_handler():
    """Aguarda conclusão de tasks ativas antes de desligar."""
    if _ACTIVE_TASKS:
        logger.info(
            "shutdown_awaiting_tasks",
            extra={"pending_tasks": len(_ACTIVE_TASKS)}
        )
        await asyncio.wait(_ACTIVE_TASKS, timeout=30)

        # Tasks que não terminaram em 30s
        if _ACTIVE_TASKS:
            logger.warning(
                "shutdown_cancelled_tasks",
                extra={"cancelled_tasks": len(_ACTIVE_TASKS)}
            )
```

**Adicionar em Cloud Run**:

```yaml
# cloudbuild.yaml - adicionar termination grace period
- name: "gcr.io/cloud-builders/gcloud"
  args:
    - run
    - deploy
    - atende-pyloto
    - --timeout=30s
    - --max-instances=10
    - --termination-grace-period=60s # Aguarda 60s antes de SIGKILL
```

**Documentar limitação**:

```markdown
# README.md - Seção "Limitações Conhecidas"

## Processamento Async sem Fila Durável

**Limitação**: Mensagens em processamento podem ser perdidas em:

- Restart manual do serviço
- Crash do processo
- Deploy com scale-down agressivo

**Mitigação atual**:

- Graceful shutdown aguarda 30s para conclusão
- Cloud Run configurado com 60s grace period
- Meta retenta mensagens não confirmadas (webhook 5xx)

**Solução futura (Fase 2)**:

- Implementar fila Redis Streams ou Cloud Tasks
- Garante durabilidade e retry controlado
```

**Prazo**: 6 horas
**Arquivos afetados**:

- `src/api/routes/whatsapp/webhook_runtime.py`
- `src/app/bootstrap/__init__.py` (adicionar shutdown handler)
- `cloudbuild.yaml`
- `README.md`

---

## 🔴 GATES OBRIGATÓRIOS (P0) - Conformidade com Padrões

### 6. **Corrigir 46 Erros de Lint (Ruff)**

**Executar e categorizar**:

```bash
ruff check . --statistics --output-format=grouped > lint_report.txt
```

**Categorias esperadas** (baseado em projetos Python similares):

- Imports não utilizados (~15 erros)
- Variáveis não utilizadas (~10 erros)
- Linhas muito longas (~8 erros)
- Type hints faltando (~8 erros)
- Outros (~5 erros)

**Correção em lote**:

```bash
# Auto-fix o que for seguro
ruff check . --fix

# Revisar manualmente o restante
ruff check . --diff
```

**Configurar Ruff corretamente**:

```toml
# pyproject.toml

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "SIM", # flake8-simplify
]

ignore = [
    "E501",  # Line too long (handled by formatter)
    "B008",  # Do not perform function calls in argument defaults (comum em FastAPI)
]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]  # Imports não usados em __init__ são OK
"tests/*" = ["S101"]       # Asserts são OK em testes
```

**Prazo**: 4 horas
**Arquivos**: Múltiplos (conforme relatório)

---

### 7. **Aumentar Cobertura de 57.65% → 80%**

**Análise de cobertura atual**:

```bash
pytest --cov=src --cov-report=html --cov-report=term-missing
# Abre htmlcov/index.html para ver arquivos sem cobertura
```

**Prioridades** (focar nos críticos primeiro):

**A. Cobertura Crítica (P0) - ~15% de ganho**:

- `src/app/use_cases/whatsapp/process_inbound_canonical.py`
- `src/app/use_cases/whatsapp/_inbound_processor.py`
- `src/ai/services/otto_agent.py`
- `src/ai/services/decision_validator.py`
- `src/app/infra/stores/redis_dedupe_store.py`

**B. Cobertura Importante (P1) - ~10% de ganho**:

- `src/ai/services/contact_card_extractor.py`
- `src/api/connectors/whatsapp/webhook/handler.py`
- `src/fsm/manager/fsm_manager.py`

**Criar testes obrigatórios**:

```python
# tests/test_app/use_cases/whatsapp/test_process_inbound_canonical.py

@pytest.mark.asyncio
async def test_process_inbound_canonical_text_message(
    mock_normalizer,
    mock_session_manager,
    mock_dedupe,
    mock_otto_agent,
    mock_outbound_sender,
):
    """Testa fluxo completo com mensagem de texto."""
    use_case = ProcessInboundCanonicalUseCase(
        normalizer=mock_normalizer,
        session_manager=mock_session_manager,
        dedupe=mock_dedupe,
        otto_agent=mock_otto_agent,
        outbound_sender=mock_outbound_sender,
    )

    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "id": "msg_123",
                        "from": "5544988887777",
                        "type": "text",
                        "text": {"body": "Olá, quero saber sobre SaaS"}
                    }]
                }
            }]
        }]
    }

    result = await use_case.execute(
        payload=payload,
        correlation_id="test_corr_123",
        tenant_id="pyloto"
    )

    assert result.processed == 1
    assert result.sent == 1
    assert result.skipped == 0
    assert result.final_state in ("TRIAGE", "COLLECTING_INFO")

@pytest.mark.asyncio
async def test_process_inbound_dedupe_skips_duplicate():
    """Testa que mensagem duplicada é ignorada."""
    # ... implementar
    assert result.skipped == 1

@pytest.mark.asyncio
async def test_process_inbound_handles_audio_transcription():
    """Testa transcrição de áudio."""
    # ... implementar quando TranscriptionAgent existir
```

```python
# tests/test_app/infra/stores/test_redis_dedupe_store.py

@pytest.mark.asyncio
async def test_redis_dedupe_atomic_operations():
    """Valida atomicidade em operações de dedupe."""
    # ... implementar com fixture de Redis

@pytest.mark.asyncio
async def test_redis_dedupe_ttl_expiration():
    """Valida que dedupe expira após TTL."""
    # ... implementar
```

```python
# tests/test_ai/services/test_otto_agent.py

@pytest.mark.asyncio
async def test_otto_agent_returns_valid_decision():
    """Valida que Otto retorna decisão estruturada válida."""
    # ... mock OpenAI client
    # ... validar OttoDecision schema

@pytest.mark.asyncio
async def test_otto_agent_fallback_on_client_error():
    """Testa fallback quando OpenAI falha."""
    # ... implementar
```

**Prazo**: 3 dias
**Meta**: 80% de cobertura em arquivos críticos

---

## 🟠 IMPLEMENTAÇÕES FALTANTES (P1)

### 8. **Implementar TranscriptionAgent**

**Criar serviço**:

```python
# src/ai/services/transcription_agent.py

from dataclasses import dataclass
from openai import AsyncOpenAI

@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    language: str
    duration_ms: float

class TranscriptionAgentService:
    """Serviço de transcrição de áudio via Whisper API."""

    def __init__(self, openai_client: AsyncOpenAI):
        self._client = openai_client

    async def transcribe(
        self,
        audio_url: str,
        language: str = "pt",
        timeout: float = 30.0,
    ) -> TranscriptionResult:
        """Transcreve áudio do WhatsApp."""
        import time
        import httpx

        start = time.perf_counter()

        try:
            # 1. Download do áudio
            async with httpx.AsyncClient(timeout=10.0) as http:
                audio_response = await http.get(audio_url)
                audio_response.raise_for_status()
                audio_bytes = audio_response.content

            # 2. Transcrição via Whisper
            transcription = await asyncio.wait_for(
                self._client.audio.transcriptions.create(
                    model="whisper-1",
                    file=("audio.ogg", audio_bytes, "audio/ogg"),
                    language=language,
                ),
                timeout=timeout
            )

            duration_ms = (time.perf_counter() - start) * 1000

            # Whisper não retorna confidence explícito
            # Usar heurística: texto muito curto = baixa confidence
            confidence = 0.9 if len(transcription.text) > 10 else 0.6

            return TranscriptionResult(
                text=transcription.text,
                confidence=confidence,
                language=language,
                duration_ms=duration_ms,
            )

        except asyncio.TimeoutError:
            logger.warning("transcription_timeout", extra={"audio_url": audio_url})
            return TranscriptionResult(
                text="",
                confidence=0.0,
                language=language,
                duration_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception as exc:
            logger.error(
                "transcription_failed",
                extra={
                    "audio_url": audio_url,
                    "error_type": type(exc).__name__,
                }
            )
            raise
```

**Integrar no processor**:

```python
# src/app/use_cases/whatsapp/_inbound_processor.py

async def _resolve_user_text(self, msg, session, correlation_id):
    if msg.message_type == "audio" and self._transcription_service:
        result = await self._transcription_service.transcribe(
            audio_url=msg.media_url,
            language="pt"
        )

        if result.confidence < 0.5:
            # Confidence muito baixa, pedir texto
            await self._outbound_sender.send(
                recipient=msg.sender_id,
                message=OutboundMessage(
                    text="Não consegui entender o áudio. Pode enviar texto?"
                ),
                correlation_id=correlation_id
            )
            return None, True

        return result.text, False

    # ... resto do código
```

**Prazo**: 1 dia
**Arquivos**:

- `src/ai/services/transcription_agent.py` (CRIAR)
- `src/app/use_cases/whatsapp/_inbound_processor.py` (atualizar)
- `tests/test_ai/services/test_transcription_agent.py` (CRIAR)

---

### 9. **Implementar Gate 3 do DecisionValidator**

**Atualizar validador**:

```python
# src/ai/services/decision_validator.py

class DecisionValidatorService:
    def __init__(self, openai_client: AsyncOpenAI | None = None):
        self._openai_client = openai_client
        self._llm_review_enabled = openai_client is not None

    async def validate(
        self,
        decision: OttoDecision,
        request: OttoRequest,
    ) -> ValidationResult:
        """Pipeline 3-gate de validação."""

        # Gate 1: Validações determinísticas
        gate1 = self._validate_deterministic(decision, request)
        if not gate1.approved:
            return gate1

        # Gate 2: Confidence check
        if decision.confidence >= 0.85:
            return ValidationResult(approved=True, gate="confidence_high")

        if decision.confidence < 0.7:
            return ValidationResult(
                approved=False,
                gate="confidence_low",
                requires_human=True,
                reason="confidence_below_threshold"
            )

        # Gate 3: LLM review (zona cinza 0.7-0.85)
        if self._llm_review_enabled:
            gate3 = await self._llm_review(decision, request)
            return gate3

        # Fallback: aprovar com flag de incerteza
        return ValidationResult(
            approved=True,
            gate="confidence_medium",
            metadata={"requires_monitoring": True}
        )

    async def _llm_review(
        self,
        decision: OttoDecision,
        request: OttoRequest,
    ) -> ValidationResult:
        """Gate 3: Revisão leve via gpt-4o-mini."""
        prompt = f"""Revise esta decisão de atendimento:

Usuário: {request.user_message}
Resposta: {decision.response_text}
Estado: {request.session_state} → {decision.next_state}
Confidence: {decision.confidence}

Critérios:
1. Resposta é adequada ao contexto?
2. Transição de estado faz sentido?
3. Tom é profissional e útil?

Retorne JSON: {{"approved": true/false, "reason": "..."}}"""

        try:
            response = await asyncio.wait_for(
                self._openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    max_tokens=100,
                ),
                timeout=3.0
            )

            review = json.loads(response.choices[0].message.content)

            return ValidationResult(
                approved=review["approved"],
                gate="llm_review",
                reason=review.get("reason"),
                requires_human=not review["approved"],
            )

        except asyncio.TimeoutError:
            # Timeout: aprovar com flag
            return ValidationResult(
                approved=True,
                gate="llm_review_timeout",
                metadata={"requires_monitoring": True}
            )
        except Exception as exc:
            logger.warning("llm_review_failed", extra={"error": str(exc)})
            # Erro: aprovar com flag
            return ValidationResult(
                approved=True,
                gate="llm_review_error",
                metadata={"requires_monitoring": True}
            )
```

**Prazo**: 6 horas
**Arquivos**:

- `src/ai/services/decision_validator.py`
- `tests/test_ai/services/test_decision_validator.py`

---

### 10. **Corrigir Estados FSM para Strings Explícitas**

**Problema atual**:

```python
# src/fsm/states/session.py usa auto()
class SessionState(Enum):
    INITIAL = auto()  # Gera int, pode variar entre versões
```

**Correção**:

```python
# src/fsm/states/session.py

class SessionState(str, Enum):
    """Estados canônicos com valores string explícitos."""

    INITIAL = "INITIAL"
    TRIAGE = "TRIAGE"
    COLLECTING_INFO = "COLLECTING_INFO"
    GENERATING_RESPONSE = "GENERATING_RESPONSE"

    HANDOFF_HUMAN = "HANDOFF_HUMAN"
    SELF_SERVE_INFO = "SELF_SERVE_INFO"
    ROUTE_EXTERNAL = "ROUTE_EXTERNAL"
    SCHEDULED_FOLLOWUP = "SCHEDULED_FOLLOWUP"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"

    def __str__(self) -> str:
        return self.value
```

**Migração de dados existentes** (se necessário):

```python
# scripts/migrate_session_states.py

async def migrate_session_states():
    """Migra estados numéricos para strings."""
    # Mapeamento auto() antigo
    OLD_TO_NEW = {
        1: "INITIAL",
        2: "TRIAGE",
        # ... resto do mapeamento
    }

    # Atualizar Firestore
    sessions = firestore_client.collection("sessions").stream()
    for session in sessions:
        data = session.to_dict()
        if isinstance(data.get("current_state"), int):
            new_state = OLD_TO_NEW.get(data["current_state"])
            if new_state:
                session.reference.update({"current_state": new_state})
```

**Prazo**: 2 horas
**Arquivos**:

- `src/fsm/states/session.py`
- `scripts/migrate_session_states.py` (CRIAR se necessário)

---

### 11. **Adicionar Validação de Transições FSM**

**Criar regras de transição**:

```python
# src/fsm/transitions/rules.py

from src.fsm.states.session import SessionState

VALID_TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.INITIAL: {
        SessionState.TRIAGE,
        SessionState.ERROR,
    },
    SessionState.TRIAGE: {
        SessionState.COLLECTING_INFO,
        SessionState.SELF_SERVE_INFO,
        SessionState.HANDOFF_HUMAN,
        SessionState.ERROR,
    },
    SessionState.COLLECTING_INFO: {
        SessionState.COLLECTING_INFO,  # Loop para coletar mais dados
        SessionState.GENERATING_RESPONSE,
        SessionState.HANDOFF_HUMAN,
        SessionState.ERROR,
    },
    SessionState.GENERATING_RESPONSE: {
        SessionState.TRIAGE,  # Nova dúvida
        SessionState.SELF_SERVE_INFO,
        SessionState.SCHEDULED_FOLLOWUP,
        SessionState.HANDOFF_HUMAN,
        SessionState.ROUTE_EXTERNAL,
        SessionState.ERROR,
    },
    # Estados terminais não têm transições
    SessionState.HANDOFF_HUMAN: set(),
    SessionState.SELF_SERVE_INFO: set(),
    SessionState.ROUTE_EXTERNAL: set(),
    SessionState.SCHEDULED_FOLLOWUP: set(),
    SessionState.TIMEOUT: set(),
    SessionState.ERROR: set(),
}

def is_valid_transition(
    from_state: SessionState,
    to_state: SessionState
) -> bool:
    """Valida se transição é permitida."""
    return to_state in VALID_TRANSITIONS.get(from_state, set())
```

**Aplicar validação no processor**:

```python
# src/app/use_cases/whatsapp/_inbound_processor_mixin.py

def _maybe_adjust_next_state(
    self,
    decision: OttoDecision,
    request: OttoRequest,
    contact_card: Any,
    correlation_id: str,
    message_id: str | None,
) -> OttoDecision:
    """Ajusta estado respeitando transições válidas."""
    from fsm.transitions.rules import is_valid_transition

    current_state = SessionState(request.session_state)
    next_state = SessionState(decision.next_state)

    # Valida transição
    if not is_valid_transition(current_state, next_state):
        logger.warning(
            "invalid_fsm_transition",
            extra={
                "component": "fsm_validator",
                "from_state": current_state.value,
                "to_state": next_state.value,
                "correlation_id": correlation_id,
                "message_id": message_id,
            }
        )

        # Fallback: manter estado atual
        return decision.model_copy(update={"next_state": current_state.value})

    return decision
```

**Prazo**: 4 horas
**Arquivos**:

- `src/fsm/transitions/rules.py` (CRIAR)
- `src/app/use_cases/whatsapp/_inbound_processor_mixin.py`
- `tests/test_fsm/test_transitions.py` (CRIAR)

---

## 🟡 REFATORAÇÕES E MELHORIAS (P2)

### 12. **Quebrar `_inbound_processor_mixin.py` (300+ linhas)**

**Estratégia**:

```
_inbound_processor_mixin.py (300+ linhas)
  ↓ dividir em ↓
├── _inbound_processor_context.py   (contexto/prompt building)
├── _inbound_processor_contact.py   (contact card operations)
└── _inbound_processor_dispatch.py  (outbound sending)
```

**Prazo**: 4 horas
**Prioridade**: P2 (funcional, mas viola padrões)

---

### 13. **Adicionar Timeouts nos `asyncio.gather`**

```python
# src/app/use_cases/whatsapp/_inbound_processor.py

async def _run_agents(...):
    try:
        decision, extraction = await asyncio.wait_for(
            asyncio.gather(
                self._otto_agent.decide(otto_request),
                self._contact_card_extractor.extract(...) if self._contact_card_extractor else _dummy_extraction(),
            ),
            timeout=5.0  # 5s máximo para ambos
        )
    except asyncio.TimeoutError:
        logger.warning("agents_timeout", ...)
        # Fallback: usar apenas Otto (extractor falhou)
        decision = await self._otto_agent.decide(otto_request)
        extraction = None

    return otto_request, decision, extraction
```

**Prazo**: 2 horas

---

### 14. **Cache de Contextos YAML no Bootstrap**

```python
# src/app/bootstrap/context_cache.py

from functools import lru_cache

@lru_cache(maxsize=50)
def load_context_cached(path: str) -> str:
    """Carrega contexto YAML com cache."""
    from ai.config.prompt_assets_loader import load_context_for_prompt
    return load_context_for_prompt(path)
```

**Prazo**: 2 horas

---

### 15. **Teste E2E Golden Path**

```python
# tests/test_e2e/test_golden_path.py

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_conversation_saas_interest(
    test_client,
    redis_client,
    firestore_client,
):
    """Testa fluxo completo: saudação → interesse SaaS → coleta email → resposta."""

    # 1. Primeira mensagem: saudação
    response = await test_client.post(
        "/webhook/whatsapp/",
        json=create_whatsapp_payload(
            message_id="msg_001",
            from_number="5544988887777",
            text="Olá"
        ),
        headers={"X-Hub-Signature-256": "..."}
    )
    assert response.status_code == 200

    # Aguarda processamento
    await asyncio.sleep(2)

    # Valida sessão criada
    session = await firestore_client.collection("sessions").document("5544988887777").get()
    assert session.exists
    assert session.to_dict()["current_state"] == "TRIAGE"

    # 2. Segunda mensagem: interesse
    response = await test_client.post(
        "/webhook/whatsapp/",
        json=create_whatsapp_payload(
            message_id="msg_002",
            from_number="5544988887777",
            text="Quero saber sobre o SaaS da Pyloto"
        ),
    )

    # Valida transição de estado
    session = await firestore_client.collection("sessions").document("5544988887777").get()
    assert session.to_dict()["current_state"] in ("COLLECTING_INFO", "GENERATING_RESPONSE")

    # Valida ContactCard
    contact = await firestore_client.collection("contact_cards").document("5544988887777").get()
    assert contact.to_dict()["primary_interest"] == "saas"

    # ... continuar fluxo
```

**Prazo**: 1 dia

---

## 📊 RESUMO DE PRIORIDADES

### **Crítico (P0) - Deploy Blocker**

| \#  | Item                   | Prazo  | Status      |
| :-- | :--------------------- | :----- | :---------- |
| 1   | Race condition dedupe  | 1 dia  | ❌          |
| 2   | Webhook error handling | 4h     | ❌          |
| 3   | Readiness check        | 1 dia  | ❌          |
| 4   | Validação de config    | 4h     | ❌          |
| 5   | Async sem durabilidade | 6h     | ❌          |
| 6   | Corrigir 46 erros lint | 4h     | ❌          |
| 7   | Cobertura 80%          | 3 dias | ❌ (57.65%) |

**Total P0**: ~6 dias úteis

### **Importante (P1) - MVP Completo**

| \#  | Item                 | Prazo | Status |
| :-- | :------------------- | :---- | :----- |
| 8   | TranscriptionAgent   | 1 dia | ❌     |
| 9   | Gate 3 validator     | 6h    | ❌     |
| 10  | Estados FSM string   | 2h    | ❌     |
| 11  | Validação transições | 4h    | ❌     |

**Total P1**: ~2 dias úteis

### **Desejável (P2) - Polish**

| \#  | Item            | Prazo |
| :-- | :-------------- | :---- |
| 12  | Refatorar mixin | 4h    |
| 13  | Timeouts gather | 2h    |
| 14  | Cache contextos | 2h    |
| 15  | Teste E2E       | 1 dia |

---

## 🎯 PLANO DE EXECUÇÃO RECOMENDADO

### **Semana 1 (5 dias)**

- **Dia 1-2**: P0.1, P0.2, P0.3, P0.4 (infraestrutura crítica)
- **Dia 3**: P0.5 (async durability) + P0.6 (lint)
- **Dia 4-5**: P0.7 (testes para 80%)

### **Semana 2 (3 dias)**

- **Dia 6**: P1.8 (TranscriptionAgent) + P1.10 (FSM strings)
- **Dia 7**: P1.9 (Gate 3) + P1.11 (validação transições)
- **Dia 8**: Deploy staging + validação 48h

### **Semana 3 (opcional)**

- P2: Refatorações e polish

**Pronto para produção**: Fim da Semana 2
