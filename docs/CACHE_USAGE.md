# Cache de Contextos YAML - Guia de Uso

**Módulo:** `src/ai/utils/context_cache.py`
**Criado em:** P2-1 (2026-02-11)

---

## 📖 Visão Geral

O cache inteligente de contextos reduz I/O repetido ao carregar YAMLs de contextos/prompts em memória com TTL (Time-To-Live) configurável.

**Benefícios:**
- ✅ Reduz latência de carregamento de YAML de ~1-2ms para ~0ms (cache hit)
- ✅ Diminui carga no filesystem em alta concorrência
- ✅ Thread-safe para uso em ambientes assíncronos (FastAPI/Starlette)
- ✅ Logs estruturados de hit/miss para análise de performance

---

## 🚀 Uso Básico

### Carregamento automático (integrado)

O cache já está integrado em `prompt_micro_agents_context.py`:

```python
from ai.services.prompt_micro_agents_context import load_yaml

# Carrega YAML com cache automático (TTL 5min)
data = load_yaml(Path("/path/to/context.yaml"))
```

### Uso direto (controle manual)

```python
from pathlib import Path
from ai.utils.context_cache import load_yaml_cached

# Carrega com TTL customizado
data = load_yaml_cached(
    path=Path("/path/to/context.yaml"),
    ttl_seconds=600  # 10 minutos
)
```

---

## 🔧 API Completa

### `load_yaml_cached(path, ttl_seconds=300)`

Carrega YAML do cache ou filesystem.

**Parâmetros:**
- `path: Path` — Caminho absoluto do arquivo YAML
- `ttl_seconds: int` — Time-to-live em segundos (padrão: 300s = 5min)

**Retorna:**
- `dict[str, Any]` — Conteúdo do YAML ou `{}` se inválido/não encontrado

**Exemplo:**

```python
from pathlib import Path
from ai.utils.context_cache import load_yaml_cached

yaml_path = Path(__file__).parent / "contexts" / "core.yaml"
data = load_yaml_cached(yaml_path, ttl_seconds=300)

if data:
    print(f"Loaded version: {data.get('version')}")
```

---

### `clear_cache()`

Limpa todo o cache manualmente.

**Uso típico:**
- Deploy de nova versão com YAMLs alterados
- Testes que requerem reload forçado

**Exemplo:**

```python
from ai.utils.context_cache import clear_cache

# Limpa cache após deploy
clear_cache()
```

---

### `invalidate_key(key)`

Invalida entrada específica do cache.

**Parâmetros:**
- `key: str` — Caminho absoluto do arquivo YAML (mesmo formato de `path.resolve()`)

**Uso típico:**
- Atualização manual de arquivo durante desenvolvimento
- Rollback de versão de prompt específico

**Exemplo:**

```python
from ai.utils.context_cache import invalidate_key
from pathlib import Path

yaml_path = Path(__file__).parent / "contexts" / "core.yaml"
cache_key = str(yaml_path.resolve())

# Invalida apenas este arquivo
invalidate_key(cache_key)

# Próximo load será cache miss
data = load_yaml_cached(yaml_path)
```

---

### `get_cache_stats()`

Retorna estatísticas do cache.

**Retorna:**
- `dict[str, int]` com chaves:
  - `total_entries`: Número de entradas no cache
  - `total_size_bytes`: Tamanho estimado em bytes

**Uso típico:**
- Monitoramento de saúde do cache
- Debug de uso de memória

**Exemplo:**

```python
from ai.utils.context_cache import get_cache_stats

stats = get_cache_stats()
print(f"Cache entries: {stats['total_entries']}")
print(f"Cache size: {stats['total_size_bytes']} bytes")
```

---

### `enable_cache()` / `disable_cache()`

Ativa/desativa cache globalmente.

**Uso típico:**
- Desabilitar cache em testes para garantir reload do disco
- Habilitar cache após testes

**Exemplo:**

```python
from ai.utils.context_cache import disable_cache, enable_cache, load_yaml_cached

# Desabilita cache para teste
disable_cache()
data1 = load_yaml_cached(yaml_path)  # sempre lê do disco

# Reabilita cache
enable_cache()
data2 = load_yaml_cached(yaml_path)  # usa cache normalmente
```

---

## 📊 Logs Estruturados

O cache registra eventos via logs estruturados JSON:

### Cache Hit

```json
{
  "component": "context_cache",
  "action": "load",
  "result": "hit",
  "key": "/path/to/context.yaml",
  "age_seconds": 42.5
}
```

**Interpretação:** Arquivo carregado do cache, idade 42.5s desde carregamento original.

---

### Cache Miss

```json
{
  "component": "context_cache",
  "action": "load",
  "result": "miss",
  "key": "/path/to/context.yaml"
}
```

**Interpretação:** Arquivo não estava no cache, carregado do filesystem.

---

### Cache Expired

```json
{
  "component": "context_cache",
  "action": "load",
  "result": "expired",
  "key": "/path/to/context.yaml",
  "age_seconds": 305.2
}
```

**Interpretação:** Entrada estava no cache mas TTL expirou (305.2s > 300s), recarregado do filesystem.

---

### Cache Cleared

```json
{
  "component": "context_cache",
  "action": "clear",
  "result": "ok",
  "items_cleared": 15
}
```

**Interpretação:** Cache limpo manualmente, 15 entradas removidas.

---

## 🎯 Casos de Uso

### 1. Warmup do cache no bootstrap

```python
from pathlib import Path
from ai.utils.context_cache import load_yaml_cached

def warmup_cache():
    """Pre-carrega YAMLs críticos no cache."""
    critical_yamls = [
        "src/ai/contexts/core/system_role.yaml",
        "src/ai/contexts/core/guardrails.yaml",
        "src/ai/contexts/core/mindset.yaml",
        # ... outros críticos ...
    ]

    for yaml_path in critical_yamls:
        load_yaml_cached(Path(yaml_path), ttl_seconds=600)

    print(f"Cache warmed with {len(critical_yamls)} YAMLs")

# Chamar no bootstrap da aplicação
warmup_cache()
```

---

### 2. Invalidação após deploy

```python
from ai.utils.context_cache import clear_cache
import logging

logger = logging.getLogger(__name__)

def post_deploy_hook():
    """Hook executado após deploy para limpar cache."""
    logger.info("Clearing context cache after deploy")
    clear_cache()
    logger.info("Cache cleared successfully")
```

---

### 3. Monitoramento de performance

```python
import time
from ai.utils.context_cache import load_yaml_cached, get_cache_stats

# Medir latência de carregamento
start = time.perf_counter()
data = load_yaml_cached(yaml_path)
latency_ms = (time.perf_counter() - start) * 1000

# Verificar estatísticas
stats = get_cache_stats()

print(f"Load latency: {latency_ms:.2f}ms")
print(f"Cache entries: {stats['total_entries']}")
```

---

### 4. Testes determinísticos

```python
import pytest
from ai.utils.context_cache import disable_cache, enable_cache, clear_cache

@pytest.fixture(autouse=True)
def no_cache():
    """Desabilita cache para testes determinísticos."""
    disable_cache()
    clear_cache()
    yield
    enable_cache()

def test_load_yaml():
    # Cache está desabilitado, sempre lê do disco
    data = load_yaml_cached(yaml_path)
    assert data["version"] == "1.0.0"
```

---

## ⚙️ Configuração

### TTL Recomendado por Tipo

| Tipo de YAML              | TTL Recomendado | Justificativa                              |
| :------------------------ | :-------------- | :----------------------------------------- |
| **Core contexts**         | 600s (10min)    | Raramente mudam, críticos                  |
| **Vertente contexts**     | 300s (5min)     | Mudam moderadamente                        |
| **Cases**                 | 300s (5min)     | Podem ser adicionados frequentemente       |
| **ROI hints**             | 180s (3min)     | Podem ter ajustes de preços/valores        |
| **Prompts de agentes**    | 600s (10min)    | Versões controladas, raramente mudam       |

---

### Estimativa de Uso de Memória

**Por YAML no cache:**
- Tamanho médio de context YAML: ~500-2000 bytes
- Overhead de cache (key, timestamp): ~200 bytes

**Cenário típico (30 YAMLs carregados):**
- 30 × (1000 bytes YAML + 200 bytes overhead) = ~36 KB
- **Conclusão:** Impacto de memória negligível (<100 KB)

---

## 🐛 Debug e Troubleshooting

### Cache hit rate baixo

**Sintoma:** Muitos logs de `cache_miss`, poucos `cache_hit`

**Possíveis causas:**
1. TTL muito curto (aumentar `ttl_seconds`)
2. Carga de YAMLs diferentes a cada requisição (esperado)
3. Cache sendo limpo frequentemente (verificar chamadas a `clear_cache()`)

**Como diagnosticar:**
```python
from ai.utils.context_cache import get_cache_stats

# Verificar no meio de carga de trabalho
stats = get_cache_stats()
print(f"Entries: {stats['total_entries']}")  # Deve crescer até estabilizar
```

---

### Cache não expirando

**Sintoma:** Mudanças em YAMLs não refletidas no sistema

**Solução:**
```python
from ai.utils.context_cache import clear_cache

# Forçar reload após mudança manual de YAML
clear_cache()
```

**Prevenção:** Usar `invalidate_key()` ao invés de `clear_cache()` para invalidar apenas arquivo específico.

---

### Testes falhando intermitentemente

**Sintoma:** Testes passam/falham aleatoriamente

**Causa provável:** Cache interferindo com testes

**Solução:** Usar fixture pytest para desabilitar cache:
```python
@pytest.fixture(autouse=True)
def clean_cache():
    disable_cache()
    clear_cache()
    yield
    enable_cache()
```

---

## 📈 Métricas de Performance

**Latência de carregamento de YAML:**

| Cenário                   | Latência   | Notas                          |
| :------------------------ | :--------- | :----------------------------- |
| **Filesystem read**       | 1-2ms      | Sem cache                      |
| **Cache hit**             | <0.1ms     | ~10-20x mais rápido            |
| **Cache miss**            | 1-2ms      | Equivalente a filesystem read  |

**Cache hit rate esperado:**
- Após 10 requisições: ~30-50% (warmup)
- Após 100 requisições: ~70-80% (estabilizado)
- Produção steady-state: ~75-85%

---

## 🔒 Thread-Safety

O cache usa `threading.Lock` para garantir thread-safety:

```python
with _cache_lock:
    # Operações no cache são atômicas
    _cache[key] = data
    _cache_timestamps[key] = now
```

**Seguro para:**
- ✅ FastAPI/Starlette (múltiplas requisições concorrentes)
- ✅ Gunicorn workers (cada worker tem seu próprio cache)
- ✅ AsyncIO tasks (lock é thread-safe, não async-safe, mas funciona)

**Nota:** Cache não é compartilhado entre processos. Cada worker Gunicorn tem seu próprio cache em memória.

---

## 📚 Referências

- [CHANGELOG_P2.md](../CHANGELOG_P2.md) — Documentação completa da implementação P2-1
- [README.md](../README.md) — Arquitetura do sistema
- [REGRAS_E_PADROES.md](../REGRAS_E_PADROES.md) — Padrões do repositório

---

**Última atualização:** 2026-02-11
**Versão:** 1.0.0 (P2-1)
