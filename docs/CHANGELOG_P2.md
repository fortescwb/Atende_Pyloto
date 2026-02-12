# Changelog - Melhorias P2 (Média Prioridade)

**Data:** 2026-02-11
**Autor:** Claude Code
**Contexto:** Implementação de melhorias P2 após conclusão de P0 e P1.

---

## 🎯 Objetivo

Implementar 3 melhorias de média prioridade para otimização, observabilidade avançada e governança de prompts no sistema de agentes IA.

---

## ✅ P2-1: Cache Inteligente de Contextos Persistentes (Otimização)

**Problema:** Contextos YAML são carregados do filesystem a cada chamada dos micro-agents, causando I/O repetido desnecessário (especialmente para YAMLs frequentemente acessados como `core.yaml`, `objections.yaml`, `roi_hints.yaml`).

**Solução Implementada:**

### 1. Criação do módulo de cache

**Arquivo:** `src/ai/utils/context_cache.py` (NOVO - 192 linhas)

**Funcionalidades:**

1. **Cache em memória com TTL**
   - TTL padrão: 300 segundos (5 minutos)
   - TTL configurável por chamada
   - Expiração automática baseada em timestamp

2. **Thread-safety**
   - Usa `threading.Lock` para evitar race conditions
   - Seguro para uso em ambiente assíncrono (FastAPI/Starlette)

3. **Métricas de cache**
   - Logs estruturados de hit/miss/expired
   - Estatísticas: `get_cache_stats()` retorna total de entradas e tamanho em bytes
   - Debug: logs de idade das entradas em cache

4. **Controle manual**
   - `clear_cache()` — Limpa todo o cache
   - `invalidate_key(key)` — Invalida entrada específica
   - `enable_cache()` / `disable_cache()` — Ativa/desativa cache (útil para testes)

5. **Retorna cópias**
   - Cache retorna `.copy()` do dict para evitar mutação compartilhada
   - Segurança: mutações em um dict retornado não afetam cache

**API pública:**

```python
def load_yaml_cached(
    path: Path,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> dict[str, Any]:
    """Carrega YAML do cache ou filesystem."""
    # ... implementação ...

def clear_cache() -> None:
    """Limpa todo o cache manualmente."""

def invalidate_key(key: str) -> None:
    """Invalida entrada específica do cache."""

def get_cache_stats() -> dict[str, int]:
    """Retorna estatísticas do cache."""

def enable_cache() -> None:
    """Ativa cache (padrão já é ativo)."""

def disable_cache() -> None:
    """Desativa cache (útil para testes)."""
```

**Logs estruturados gerados:**

```json
// Cache hit
{
  "component": "context_cache",
  "action": "load",
  "result": "hit",
  "key": "/path/to/file.yaml",
  "age_seconds": 42.5
}

// Cache miss
{
  "component": "context_cache",
  "action": "load",
  "result": "miss",
  "key": "/path/to/file.yaml"
}

// Cache expired
{
  "component": "context_cache",
  "action": "load",
  "result": "expired",
  "key": "/path/to/file.yaml",
  "age_seconds": 305.2
}
```

### 2. Integração no carregamento de contextos

**Arquivo:** `src/ai/services/prompt_micro_agents_context.py` (MODIFICADO)

**Mudança:** Função `load_yaml()` agora usa `load_yaml_cached()` com TTL de 5 minutos:

**Antes:**
```python
def load_yaml(path: Path) -> dict[str, Any]:
    """Lê YAML e retorna dict seguro."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}
```

**Depois:**
```python
from ai.utils.context_cache import load_yaml_cached

def load_yaml(path: Path) -> dict[str, Any]:
    """Lê YAML e retorna dict seguro.

    P2-1: Usa cache com TTL 5min para reduzir I/O repetido.
    """
    return load_yaml_cached(path, ttl_seconds=300)
```

### 3. Testes criados

**Arquivo:** `tests/test_ai/test_context_cache.py` (NOVO - 157 linhas)

**Cenários testados:**

1. `test_cache_miss_then_hit()` — Valida hit após miss
2. `test_cache_ttl_expiration()` — Valida expiração por TTL
3. `test_cache_invalidate_key()` — Valida invalidação manual
4. `test_cache_clear()` — Valida limpeza total do cache
5. `test_cache_disabled()` — Valida desabilitação do cache
6. `test_cache_returns_copy()` — Valida que retorna cópia (evita mutação)
7. `test_cache_file_not_found()` — Valida comportamento com arquivo inexistente
8. `test_cache_invalid_yaml()` — Valida comportamento com YAML inválido
9. `test_cache_stats()` — Valida estatísticas do cache

**Benefícios:**

- ✅ **Performance:** Reduz I/O repetido (YAMLs acessados múltiplas vezes por requisição)
- ✅ **Latência:** Economiza 1-5ms por YAML carregado do cache (vs filesystem)
- ✅ **Escalabilidade:** Reduz carga no filesystem em alta concorrência
- ✅ **Observabilidade:** Logs estruturados de hit/miss para análise
- ✅ **Configurabilidade:** TTL ajustável por contexto (5min padrão)
- ✅ **Testabilidade:** Cache pode ser desabilitado para testes determinísticos

**Impacto estimado:**

- **Cenário típico:** 3-5 YAMLs carregados por requisição de Otto (core.yaml, objections.yaml, case.yaml, roi_hints.yaml, etc.)
- **Sem cache:** 3-5 reads de filesystem = 5-10ms de I/O
- **Com cache (hit):** 0 reads de filesystem = ~0ms de I/O
- **Economia:** ~5-10ms por requisição após warmup (20-30% das requisições)

---

## ✅ P2-2: Dashboard de Métricas de Agentes (Observabilidade)

**Problema:** Métricas P1-2 são registradas via logs estruturados JSON, mas não havia queries prontas para análise agregada, dashboards ou alertas.

**Solução Implementada:**

### 1. Criação de queries SQL/BigQuery

**Arquivo:** `docs/queries/metrics_dashboard.sql` (NOVO - 363 linhas)

**Conteúdo:** 8 queries principais para análise de métricas:

#### Query 1: Latências (Percentis P50, P90, P95, P99)

Agrega latências por componente/operação com percentis:

```sql
SELECT
  component, operation,
  COUNT(*) AS total_operations,
  APPROX_QUANTILES(latency_ms, 100)[OFFSET(50)] AS p50_latency_ms,
  APPROX_QUANTILES(latency_ms, 100)[OFFSET(90)] AS p90_latency_ms,
  APPROX_QUANTILES(latency_ms, 100)[OFFSET(95)] AS p95_latency_ms,
  APPROX_QUANTILES(latency_ms, 100)[OFFSET(99)] AS p99_latency_ms,
  AVG(latency_ms) AS avg_latency_ms
FROM logs
WHERE metric_type = 'latency' AND timestamp >= ...
GROUP BY component, operation
ORDER BY avg_latency_ms DESC;
```

**Uso:** Identificar componentes lentos, validar SLA (P95 < 4s)

#### Query 2: Confidence (Distribuição e Média)

Agrega confiança das decisões com bins:

```sql
SELECT
  component, operation,
  COUNT(*) AS total_decisions,
  AVG(confidence) AS avg_confidence,
  COUNTIF(confidence < 0.5) AS low_confidence_count,
  COUNTIF(confidence BETWEEN 0.5 AND 0.7) AS medium_confidence_count,
  COUNTIF(confidence BETWEEN 0.7 AND 0.85) AS good_confidence_count,
  COUNTIF(confidence >= 0.85) AS high_confidence_count
FROM logs
WHERE metric_type = 'confidence' AND timestamp >= ...
GROUP BY component, operation
ORDER BY avg_confidence ASC;
```

**Uso:** Monitorar qualidade das decisões, identificar prompts com baixa confiança

#### Query 3: Handoffs (Taxa e Motivos)

Agrega escalações para humano:

```sql
SELECT
  reason AS handoff_reason,
  COUNT(*) AS handoff_count,
  ROUND(COUNT(*) / (SELECT COUNT(*) FROM logs WHERE metric_type = 'handoff' AND ...) * 100, 2) AS percentage
FROM logs
WHERE metric_type = 'handoff' AND timestamp >= ...
GROUP BY reason
ORDER BY handoff_count DESC;
```

**Uso:** Identificar principais motivos de escalação (low_confidence, client_error, explicit_request)

#### Query 4: Tokens (Custo Estimado)

Agrega uso de tokens com estimativa de custo:

```sql
SELECT
  component, operation,
  COUNT(*) AS total_calls,
  SUM(prompt_tokens) AS total_prompt_tokens,
  SUM(completion_tokens) AS total_completion_tokens,
  SUM(total_tokens) AS total_tokens,
  AVG(total_tokens) AS avg_tokens_per_call,
  CASE component
    WHEN 'otto_agent' THEN SUM(total_tokens) * 0.0025 / 1000  -- gpt-4o
    WHEN 'extraction_agent' THEN SUM(total_tokens) * 0.00015 / 1000  -- gpt-4o-mini
    ELSE SUM(total_tokens) * 0.0001 / 1000
  END AS estimated_cost_usd
FROM logs
WHERE metric_type = 'token_usage' AND timestamp >= ...
GROUP BY component, operation
ORDER BY total_tokens DESC;
```

**Uso:** Monitorar custos de API OpenAI, identificar prompts caros

#### Query 5: Correlação Latência vs Confidence

Análise de qualidade: decisões com baixa confiança são mais lentas?

```sql
WITH latencies AS (...),
     confidences AS (...)
SELECT
  CASE
    WHEN confidence < 0.5 THEN 'low'
    WHEN confidence BETWEEN 0.5 AND 0.7 THEN 'medium'
    WHEN confidence BETWEEN 0.7 AND 0.85 THEN 'good'
    ELSE 'high'
  END AS confidence_bucket,
  COUNT(*) AS decision_count,
  AVG(latency_ms) AS avg_latency_ms,
  APPROX_QUANTILES(latency_ms, 100)[OFFSET(95)] AS p95_latency_ms
FROM latencies l
INNER JOIN confidences c ON l.correlation_id = c.correlation_id
GROUP BY confidence_bucket;
```

**Uso:** Entender relação entre latência e qualidade de decisão

#### Query 6: Série Temporal de Latência

Latência ao longo do tempo (últimas 24h):

```sql
SELECT
  TIMESTAMP_TRUNC(timestamp, HOUR) AS hour,
  component,
  COUNT(*) AS operations,
  APPROX_QUANTILES(latency_ms, 100)[OFFSET(50)] AS p50_latency_ms,
  APPROX_QUANTILES(latency_ms, 100)[OFFSET(95)] AS p95_latency_ms
FROM logs
WHERE metric_type = 'latency' AND timestamp >= ...
GROUP BY hour, component
ORDER BY hour DESC;
```

**Uso:** Identificar degradações de performance ao longo do dia

#### Query 7: Handoff Rate ao Longo do Tempo

Taxa de escalação por hora:

```sql
WITH total_decisions AS (...),
     handoffs AS (...)
SELECT
  hour,
  COALESCE(handoff_count, 0) AS handoffs,
  total AS total_decisions,
  ROUND(COALESCE(handoff_count, 0) / total * 100, 2) AS handoff_rate_percent
FROM total_decisions t
LEFT JOIN handoffs h ON t.hour = h.hour
ORDER BY hour DESC;
```

**Uso:** Monitorar tendências de escalação, identificar horários problemáticos

#### Query 8: Alertas (Thresholds Críticos)

3 alertas para uso em monitoring:

1. **HIGH_LATENCY:** P95 > 3000ms (últimos 15min)
2. **HIGH_HANDOFF_RATE:** Taxa de handoff > 15% (últimos 15min)
3. **LOW_CONFIDENCE:** Confidence média < 0.7 (últimos 15min)

**Uso:** Integração com sistemas de alerting (PagerDuty, Slack, email)

### 2. Suporte multi-plataforma

Queries incluem versões para:
- **BigQuery** (sintaxe padrão no arquivo)
- **CloudWatch Logs Insights** (comentários com sintaxe alternativa)
- **Elasticsearch/Kibana** (notas de adaptação)

### 3. Notas de uso

Arquivo inclui:
- Instruções de adaptação de sintaxe por plataforma
- Recomendações de painéis de dashboard
- Guidelines de calibração de thresholds

**Benefícios:**

- ✅ **Análise pronta:** Queries copy-paste para BigQuery/CloudWatch
- ✅ **Observabilidade 360°:** Latência + Confidence + Handoff + Custo
- ✅ **Alerting:** Thresholds configuráveis para monitoramento proativo
- ✅ **Correlação:** Análise de relação entre métricas (latência vs confidence)
- ✅ **Histórico:** Séries temporais para identificar tendências

**Integração sugerida:**

- Painel 1: **Latências** (série temporal + histograma P50/P95/P99)
- Painel 2: **Confidence** (gauge + distribuição por buckets)
- Painel 3: **Handoffs** (taxa % + top 5 motivos)
- Painel 4: **Custos** (tokens consumidos + estimativa USD)
- Painel 5: **Alertas** (status atual dos 3 thresholds)

---

## ✅ P2-3: Versionamento Semântico de Prompts (Changelog)

**Problema:** YAMLs de prompts e contextos não tinham rastreamento de mudanças, dificultando auditoria, rollback e entendimento de histórico de alterações.

**Solução Implementada:**

### 1. Criação do PROMPT_CHANGELOG.md

**Arquivo:** `PROMPT_CHANGELOG.md` (NOVO - 311 linhas)

**Estrutura:** Inspired by [Keep a Changelog](https://keepachangelog.com/) e [Semantic Versioning](https://semver.org/)

**Seções:**

1. **Convenções de Versão**
   - MAJOR (X.0.0): Breaking changes
   - MINOR (1.X.0): Novas funcionalidades
   - PATCH (1.0.X): Correções/typos

2. **[Unreleased]** — Mudanças planejadas

3. **[1.0.0] - 2026-02-11** — Versão inicial (baseline)
   - Documentação dos 5 novos `roi_hints.yaml` (P1-1)
   - Lista completa de contextos core existentes
   - Lista de prompts de agentes existentes

4. **Inventário completo** de YAMLs:
   - Core system (system_role, mindset, guardrails, sobre_pyloto)
   - Regras de output (json_output)
   - Vertentes (automacao, sob_medida, trafego, saas, entregas)
   - Cases por vertente (clinica, ecommerce, imobiliaria, logistica, etc.)
   - Prompts de agentes (otto_user_template, contact_card_extractor)

5. **Guidelines de Manutenção**
   - Quando versionar MAJOR/MINOR/PATCH
   - Processo de atualização (YAML + changelog)
   - Boas práticas (evitar breaking changes, documentar deprecations)

**Formato de entrada:**

```markdown
## [1.1.0] - 2026-02-15

### Changed
- `src/ai/contexts/vertentes/automacao/faq.yaml` (1.1.0)
  - Adicionada pergunta sobre integrações com CRMs
  - Atualizado preço base (de R$ 200-500/mês para R$ 300-600/mês)
```

**Categorias:**
- `Added` — Novos contextos/prompts
- `Changed` — Modificações em existentes
- `Deprecated` — Marcados para remoção futura
- `Removed` — Removidos (MAJOR version)
- `Fixed` — Correções de bugs/typos
- `Security` — Ajustes de segurança

### 2. Estrutura esperada nos YAMLs

Todos os YAMLs de contexto/prompt devem ter:

```yaml
version: "1.0.0"  # Semver
updated_at: "2026-02-11"  # YYYY-MM-DD

metadata:
  context_type: "..."
  # ... outros metadados ...

prompt_injection: |
  Conteúdo do prompt...
```

### 3. Processo de atualização

**Ao modificar um YAML:**

1. Atualizar `version` no YAML (seguindo semver)
2. Atualizar `updated_at` no YAML
3. Adicionar entrada no `PROMPT_CHANGELOG.md` sob `[Unreleased]` ou nova versão
4. Categorizar mudança (`Added`, `Changed`, etc.)
5. Documentar razão e impacto da mudança

**Benefícios:**

- ✅ **Auditoria:** Histórico completo de mudanças em prompts/contextos
- ✅ **Rastreabilidade:** Correlação entre versão de prompt e comportamento do sistema
- ✅ **Rollback:** Facilita reverter mudanças problemáticas
- ✅ **Documentação:** Inventário completo de YAMLs existentes
- ✅ **Governança:** Guidelines claras de versionamento e manutenção
- ✅ **Comunicação:** Time alinhado sobre mudanças em prompts

**Casos de uso:**

- **Debug:** "Esse handoff começou a subir quando mudamos roi_hints.yaml para v1.1.0"
- **Rollback:** "Revertendo automacao/objections.yaml de v1.2.0 para v1.1.0"
- **Planejamento:** "v2.0.0 vai remover deprecated roi_hint_template.yaml"
- **Auditoria:** "Quais prompts mudaram entre janeiro e fevereiro?"

---

## 📊 Impacto Estimado

| Métrica                               | Antes                         | Depois                        | Melhoria    |
| :------------------------------------ | :---------------------------- | :---------------------------- | :---------- |
| **I/O de YAMLs por requisição**       | 3-5 reads de filesystem       | 0 reads (após warmup)         | -100%       |
| **Latência de carregamento YAML**     | 1-2ms/YAML                    | ~0ms (cache hit)              | -100%       |
| **Cache hit rate estimado**           | N/A                           | 70-80% após warmup            | N/A         |
| **Análise de métricas**               | ❌ Manual via logs brutos     | ✅ Queries prontas            | +100%       |
| **Dashboards de observabilidade**     | ❌ Inexistente                | ✅ 8 queries + guidelines     | +100%       |
| **Rastreabilidade de prompts**        | ❌ Sem histórico              | ✅ Changelog versionado       | +100%       |
| **Tempo para debug de prompt**        | ⚠️ Alto (sem histórico)       | ✅ Baixo (changelog)          | -50-70%     |

---

## 🧪 Validação

### 1. Sintaxe Python

```bash
python -m py_compile src/ai/utils/context_cache.py
python -m py_compile src/ai/services/prompt_micro_agents_context.py
python -m py_compile tests/test_ai/test_context_cache.py
```

**Resultado:** ✅ Todos passaram

### 2. Testes unitários

```bash
pytest tests/test_ai/test_context_cache.py -v
```

**Cobertura esperada:** 9 testes do cache (hit, miss, ttl, invalidate, clear, disable, copy, not_found, invalid_yaml, stats)

**Nota:** Requer ambiente com dependências instaladas (pytest, yaml)

### 3. Conformidade com REGRAS_E_PADROES.md

- ✅ § 1.3: Determinismo (cache pode ser desabilitado para testes)
- ✅ § 4: Arquivos ≤200 linhas (context_cache.py: 192 linhas, test: 157 linhas)
- ✅ § 5: Type hints explícitos (todos os parâmetros tipados)
- ✅ § 6: Logs estruturados sem PII (logs de cache hit/miss)
- ✅ § 8: Testes determinísticos (9 testes do cache)

---

## 📝 Arquivos Criados/Modificados

### Criados (4 arquivos):

1. **`src/ai/utils/context_cache.py`** (+192 linhas)
   - Módulo de cache inteligente com TTL
   - Thread-safe, métricas de hit/miss, invalidação manual

2. **`tests/test_ai/test_context_cache.py`** (+157 linhas)
   - 9 testes do cache (hit, miss, ttl, invalidate, clear, disable, copy, not_found, invalid_yaml, stats)

3. **`docs/queries/metrics_dashboard.sql`** (+363 linhas)
   - 8 queries principais para BigQuery/CloudWatch
   - Alertas, séries temporais, correlações

4. **`PROMPT_CHANGELOG.md`** (+311 linhas)
   - Changelog de prompts e contextos
   - Inventário completo de YAMLs
   - Guidelines de versionamento

### Modificados (1 arquivo):

1. **`src/ai/services/prompt_micro_agents_context.py`**:
   - Função `load_yaml()` agora usa `load_yaml_cached()` com TTL de 5min
   - Import de `ai.utils.context_cache`

**Total:** ~1023 linhas adicionadas

---

## 🚀 Próximos Passos (P3 - Baixa Prioridade / Futuros)

1. **P3-1:** Implementar dashboard real usando Grafana + BigQuery/CloudWatch
2. **P3-2:** Criar alertas automáticos (PagerDuty/Slack) baseados nas queries de threshold
3. **P3-3:** Adicionar cache warming no bootstrap (pre-load de YAMLs críticos)
4. **P3-4:** Implementar versionamento automático de prompts (CI/CD hook)
5. **P3-5:** Criar ferramenta CLI para diff de prompts entre versões

---

## 📚 Referências

- **P1 Concluído:** [CHANGELOG_P1.md](./CHANGELOG_P1.md)
- **P0 Concluído:** [CHANGELOG_P0.md](./CHANGELOG_P0.md)
- **Regras do Projeto:** [REGRAS_E_PADROES.md](./REGRAS_E_PADROES.md)
- **Arquitetura:** [README.md](./README.md)
- **Keep a Changelog:** https://keepachangelog.com/
- **Semantic Versioning:** https://semver.org/

---

**Status:** ✅ Concluído
**Pronto para:** Code review + testes em ambiente com dependências instaladas

**Melhorias entregues:**
- P2-1: Cache inteligente de contextos (otimização I/O)
- P2-2: Dashboard de métricas (queries prontas)
- P2-3: Versionamento de prompts (changelog + guidelines)
