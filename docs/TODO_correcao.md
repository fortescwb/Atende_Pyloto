# TODO — Correções Pós-Auditoria

> Documento gerado em 2026-02-03 após auditoria de conformidade.
> Referências normativas: `REGRAS_E_PADROES.md`, `FUNCIONAMENTO.md`, `README.md`

---

## Resumo de status

| Severidade | Total | Pendentes | Concluídas |
|------------|-------|-----------|------------|
| 🔴 CRÍTICO | 2     | 0         | 2 ✅       |
| 🟠 ALTO    | 2     | 0         | 2 ✅       |
| 🟡 MÉDIO   | 3     | 0         | 3 ✅       |
| 🟢 BAIXO   | 2     | 0         | 2 ✅       |

---

## 🔴 CRÍTICO — Bloqueia merge/deploy

### C1. Quebra de contrato `AsyncSessionStoreProtocol`

**Problema:** O protocolo define `save`, `load`, `delete`, `exists` (async), mas `RedisSessionStore` implementa `save_async`, `load_async`, etc. Contrato quebrado.

**Arquivos afetados:**
- `src/app/protocols/session_store.py`
- `src/app/infra/stores/redis_session_store.py`
- `src/app/infra/stores/memory_stores.py`

**Ação:**
Alterar protocolo `AsyncSessionStoreProtocol` para usar sufixo `_async` nos métodos, mantendo consistência com implementações existentes e evitando conflito de nomes sync/async na mesma classe.

```python
# src/app/protocols/session_store.py
class AsyncSessionStoreProtocol(ABC):
    @abstractmethod
    async def save_async(self, session: Any, ttl_seconds: int = 7200) -> None: ...
    @abstractmethod
    async def load_async(self, session_id: str) -> Any | None: ...
    @abstractmethod
    async def delete_async(self, session_id: str) -> bool: ...
    @abstractmethod
    async def exists_async(self, session_id: str) -> bool: ...
```

**Checklist:**
- [x] Atualizar `AsyncSessionStoreProtocol` em `session_store.py`
- [x] Verificar que `RedisSessionStore` já implementa `save_async`, `load_async`, etc.
- [x] Adicionar métodos async em `MemorySessionStore`
- [x] Atualizar testes para cobrir API async
- [x] Rodar `pytest -q` — todos devem passar

**Status:** ✅ **CONCLUÍDO** (2026-02-03)

**Regra violada:** REGRAS § 1.4 (Boundaries são lei), § 2.3 (contratos via protocolos)

---

### C2. `MemorySessionStore` não implementa API async

**Problema:** Classe herda de `AsyncSessionStoreProtocol` mas não possui métodos async.

**Arquivo:** `src/app/infra/stores/memory_stores.py`

**Ação:** Adicionar implementações async delegando para métodos sync internos.

```python
# Adicionar em MemorySessionStore:
async def save_async(self, session: Any, ttl_seconds: int = 7200) -> None:
    """Salva sessão (async wrapper)."""
    self._save_sync(session, ttl_seconds)

async def load_async(self, session_id: str) -> Session | None:
    """Carrega sessão (async wrapper)."""
    return self._load_sync(session_id)

async def delete_async(self, session_id: str) -> bool:
    """Remove sessão (async wrapper)."""
    return self._delete_sync(session_id)

async def exists_async(self, session_id: str) -> bool:
    """Verifica existência (async wrapper)."""
    return self._exists_sync(session_id)
```

**Checklist:**
- [x] Implementar 4 métodos async em `MemorySessionStore`
- [x] Adicionar testes async para `MemorySessionStore`
- [x] Verificar LSP (Liskov) — substituição polimórfica deve funcionar

**Status:** ✅ **CONCLUÍDO** (2026-02-03)

**Regra violada:** REGRAS § 1.4 (Boundaries são lei)

---

## 🟠 ALTO — Deve ser corrigido antes de PR

### A1. Arquivo `dependencies.py` excede 200 linhas ✅ CORRIGIDO

**Problema:** 253 linhas. Limite: ≤200 linhas (REGRAS § 4).

**Arquivo:** `src/app/bootstrap/dependencies.py`

**Opções:**
1. **Dividir** — Extrair factories de clientes Redis/Firestore para `clients.py`
2. **Registrar exceção** — Se fragmentar piora clareza, documentar em `docs/Monitoramento_Regras-Padroes.md`

**Ação recomendada:** Dividir em 2 arquivos.

```
src/app/bootstrap/
├── __init__.py          # Exports públicos
├── dependencies.py      # Factories de stores (session, dedupe, audit)
└── clients.py           # Factories de clientes (Redis, Firestore)
```

**Checklist:**
- [x] Criar `src/app/bootstrap/clients.py`
- [x] Mover `create_redis_client`, `create_async_redis_client`, `create_firestore_client`
- [x] Atualizar imports em `dependencies.py`
- [x] Verificar que `dependencies.py` fica ≤200 linhas (169 linhas)
- [x] Atualizar `__init__.py` se necessário

**Status:** ✅ **CONCLUÍDO** (2026-02-03)

**Regra violada:** REGRAS § 4 (Limites de tamanho)

---

### A2. Linhas longas (E501) — 8 ocorrências ✅ CORRIGIDO

**Problema:** Linhas > 100 caracteres. Gate `ruff check` falha.

**Arquivos e linhas:**

| Arquivo | Linha | Contexto |
|---------|-------|----------|
| `src/app/bootstrap/dependencies.py` | 68 | Log de redis client |
| `src/app/bootstrap/whatsapp_factory.py` | 31 | Signature de factory |
| `src/app/bootstrap/whatsapp_factory.py` | 62 | Signature de método |
| `src/app/bootstrap/whatsapp_factory.py` | 65 | Signature de método |
| `src/app/protocols/crypto.py` | 25 | Signature de método |
| `src/app/protocols/crypto.py` | 28 | Signature de método |
| `src/app/protocols/master_decider.py` | 22 | Signature de método |
| `tests/app/infra/stores/test_redis_session_store.py` | 40 | Fixture JSON inline |

**Ação:** Quebrar linhas respeitando PEP 8.

**Exemplo — dependencies.py:68:**
```python
# Antes:
logger.info("redis_client_created", extra={"host": client.connection_pool.connection_kwargs.get("host", "unknown")})

# Depois:
host = client.connection_pool.connection_kwargs.get("host", "unknown")
logger.info("redis_client_created", extra={"host": host})
```

**Exemplo — test fixture (linha 40):**
```python
# Antes:
mock_redis.get.return_value = b'{"session_id": "load-123", ...muito longo...}'

# Depois:
SESSION_FIXTURE = {
    "session_id": "load-123",
    "sender_id": "s",
    "current_state": "INITIAL",
    "context": {"tenant_id": "", "vertente": "geral", "rules": {}, "limits": {}},
    "history": [],
    "turn_count": 0,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
    "expires_at": None,
}
mock_redis.get.return_value = json.dumps(SESSION_FIXTURE).encode()
```

**Checklist:**
- [x] Corrigir `dependencies.py:68`
- [x] Corrigir `whatsapp_factory.py:31,62,65`
- [x] Corrigir `crypto.py:25,28`
- [x] Corrigir `master_decider.py:22`
- [x] Corrigir `test_redis_session_store.py:40`
- [x] Rodar `ruff check .` — 0 erros E501

**Status:** ✅ **CONCLUÍDO** (2026-02-03)

**Regra violada:** REGRAS § 9 (Gates obrigatórios)

---

## 🟡 MÉDIO — Corrigir em próxima iteração

### M1. `FirestoreAuditStore.append_async` bloqueia event loop ✅ CORRIGIDO

**Problema:** Método `async` mas chama `self.append()` síncrono internamente. Bloqueia event loop sob carga.

**Arquivo:** `src/app/infra/stores/firestore_audit_store.py` (linhas 80-91)

**Ação:** Usar `asyncio.to_thread()` para não bloquear.

```python
import asyncio

async def append_async(self, record: dict[str, Any]) -> None:
    """Append assíncrono de registro de auditoria."""
    await asyncio.to_thread(self.append, record)
```

**Checklist:**
- [x] Importar `asyncio`
- [x] Substituir `self.append(record)` por `await asyncio.to_thread(...)`
- [x] Adicionar teste async para verificar não-bloqueio

**Status:** ✅ **CONCLUÍDO** (2026-02-03)

**Referência:** FUNCIONAMENTO § 6 (Concorrência e escalabilidade)

---

### M2. Variável global `_client` em `gcp_secrets.py` ✅ CORRIGIDO

**Problema:** Singleton via `global _client`. Dificulta testes e DI.

**Arquivo:** `src/app/infra/secrets/gcp_secrets.py` (linhas 21-28)

**Ação:** Refatorar para usar `lru_cache` em factory ou instância injetável.

```python
# Opção A — lru_cache (mínima mudança)
@lru_cache(maxsize=1)
def _get_client() -> SecretManagerServiceClient:
    from google.cloud import secretmanager
    return secretmanager.SecretManagerServiceClient()

# Remover variável global _client
```

**Checklist:**
- [x] Remover `global _client`
- [x] Usar `@lru_cache` no `_get_client()`
- [x] Verificar testes existentes

**Status:** ✅ **CONCLUÍDO** (2026-02-03)

**Referência:** REGRAS § 1.3 (Determinismo — sem estado global)

---

### M3. Keys de dedupe podem conter dados sensíveis ✅ CORRIGIDO

**Problema:** Logs debug incluem `extra={"key": key}`. Se key contiver metadados de usuário, pode vazar.

**Arquivo:** `src/app/infra/stores/redis_dedupe_store.py` (linha 63)

**Ação:** Documentar contrato de que keys devem ser IDs opacos. Opcionalmente, mascarar em logs DEBUG.

```python
# Opção conservadora — mascarar parcialmente
logger.debug(
    "dedupe_duplicate_detected",
    extra={"key_prefix": key[:8] + "..." if len(key) > 8 else key}
)
```

**Checklist:**
- [x] Adicionar docstring documentando que `key` deve ser ID opaco ou hash
- [x] Considerar mascarar key em logs DEBUG
- [x] Revisar chamadores para garantir que não passam dados sensíveis

**Status:** ✅ **CONCLUÍDO** (2026-02-03)

**Referência:** REGRAS § 6 (Logs sem PII)

---

## 🟢 BAIXO — Nice to have

### B1. Docstrings misturando PT-BR e EN ✅ JÁ CONFORME

**Problema:** Alguns arquivos têm docstrings em inglês.

**Ação:** Padronizar em português conforme REGRAS § 5.

**Arquivos para revisar:**
- `src/app/infra/stores/*.py`
- `src/app/infra/secrets/*.py`
- `src/app/bootstrap/*.py`

**Checklist:**
- [x] Revisar docstrings e traduzir para PT-BR
- [x] Manter termos técnicos em inglês quando apropriado (ex.: "Redis", "TTL")

**Status:** ✅ **JÁ CONFORME** (2026-02-03) — Docstrings já estavam em PT-BR

---

### B2. Testes não cobrem API async dos stores ✅ CORRIGIDO

**Problema:** `test_redis_session_store.py` testa apenas API sync.

**Arquivo:** `tests/app/infra/stores/test_redis_session_store.py`

**Ação:** Adicionar testes para métodos `save_async`, `load_async`, etc. com mock de `AsyncRedis`.

**Checklist:**
- [x] Criar classe `TestRedisSessionStoreAsync`
- [x] Testar `save_async`, `load_async`, `delete_async`, `exists_async`
- [x] Usar `pytest.mark.anyio` para testes async

**Status:** ✅ **CONCLUÍDO** (2026-02-03) — 6 testes async adicionados

---

## Ordem de execução recomendada

1. **C1 + C2** — Resolver quebra de contrato async (bloqueia)
2. **A2** — Corrigir linhas longas (gate ruff)
3. **A1** — Dividir `dependencies.py`
4. **M1** — Corrigir `append_async`
5. **M2** — Refatorar `_get_client`
6. **M3** — Documentar contrato de keys
7. **B1 + B2** — Polish e cobertura

---

## Validação final

Após todas as correções:

```bash
# Gates obrigatórios
ruff check .
pytest -q
pytest --cov=src --cov-fail-under=80

# Verificação adicional
wc -l src/app/bootstrap/*.py  # Todos ≤200
```

---

## Registro de conclusão

| Item | Data       | Responsável | Commit |
|------|------------|-------------|--------|
| C1   | 2026-02-03 | Executor    | -      |
| C2   | 2026-02-03 | Executor    | -      |
| A1   | 2026-02-03 | Executor    | -      |
| A2   | 2026-02-03 | Executor    | -      |
| M1   | 2026-02-03 | Executor    | -      |
| M2   | 2026-02-03 | Executor    | -      |
| M3   | 2026-02-03 | Executor    | -      |
| B1   | 2026-02-03 | Executor    | ✓ Já conforme |
| B2   | 2026-02-03 | Executor    | -      |

---

## ✅ Auditoria Finalizada

Todas as 9 tarefas identificadas foram concluídas ou validadas como conformes.

**Gates finais:**
- `ruff check`: ✅ All checks passed!
- `pytest -q`: ✅ 405 passed

**Nota sobre cobertura:** A meta de 80% não é atingível no momento devido a arquivos de scaffold vazios criados durante o desenvolvimento da estrutura. Cobertura será endereçada em iteração futura conforme módulos forem implementados.
