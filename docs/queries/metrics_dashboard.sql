-- Queries para Dashboard de Métricas de Agentes IA (P2-2)
--
-- Estrutura de logs JSON esperada:
-- {
--   "metric_type": "latency|confidence|handoff|token_usage",
--   "component": "otto_agent|micro_agents|...",
--   "operation": "decide|...",
--   "correlation_id": "uuid",
--   "timestamp": "ISO8601",
--   ...campos específicos...
-- }
--
-- Plataforma: BigQuery / CloudWatch Logs Insights / Elasticsearch
--
-- IMPORTANTE: Adapte a sintaxe para sua plataforma:
-- - BigQuery: use `PARSE_JSON()`, `JSON_EXTRACT_SCALAR()`
-- - CloudWatch: use `fields`, `stats`, `filter`
-- - Elasticsearch: use agregações Kibana

-- ============================================================================
-- 1. LATÊNCIAS: Percentis P50, P90, P95, P99 por componente/operação
-- ============================================================================

-- BigQuery:
SELECT
  JSON_EXTRACT_SCALAR(json_payload, '$.component') AS component,
  JSON_EXTRACT_SCALAR(json_payload, '$.operation') AS operation,
  COUNT(*) AS total_operations,
  APPROX_QUANTILES(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.latency_ms') AS FLOAT64), 100)[OFFSET(50)] AS p50_latency_ms,
  APPROX_QUANTILES(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.latency_ms') AS FLOAT64), 100)[OFFSET(90)] AS p90_latency_ms,
  APPROX_QUANTILES(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.latency_ms') AS FLOAT64), 100)[OFFSET(95)] AS p95_latency_ms,
  APPROX_QUANTILES(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.latency_ms') AS FLOAT64), 100)[OFFSET(99)] AS p99_latency_ms,
  AVG(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.latency_ms') AS FLOAT64)) AS avg_latency_ms
FROM
  `pyloto-prod.logs.atende_pyloto`
WHERE
  JSON_EXTRACT_SCALAR(json_payload, '$.metric_type') = 'latency'
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY
  component, operation
ORDER BY
  avg_latency_ms DESC;

-- CloudWatch Logs Insights:
-- fields @timestamp, component, operation, latency_ms
-- | filter metric_type = "latency"
-- | stats pct(latency_ms, 50) as p50, pct(latency_ms, 90) as p90, pct(latency_ms, 95) as p95, pct(latency_ms, 99) as p99, avg(latency_ms) as avg by component, operation
-- | sort avg desc


-- ============================================================================
-- 2. CONFIDENCE: Distribuição e média por componente/operação
-- ============================================================================

-- BigQuery:
SELECT
  JSON_EXTRACT_SCALAR(json_payload, '$.component') AS component,
  JSON_EXTRACT_SCALAR(json_payload, '$.operation') AS operation,
  COUNT(*) AS total_decisions,
  AVG(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.confidence') AS FLOAT64)) AS avg_confidence,
  STDDEV(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.confidence') AS FLOAT64)) AS stddev_confidence,
  -- Bins de confidence
  COUNTIF(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.confidence') AS FLOAT64) < 0.5) AS low_confidence_count,
  COUNTIF(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.confidence') AS FLOAT64) BETWEEN 0.5 AND 0.7) AS medium_confidence_count,
  COUNTIF(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.confidence') AS FLOAT64) BETWEEN 0.7 AND 0.85) AS good_confidence_count,
  COUNTIF(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.confidence') AS FLOAT64) >= 0.85) AS high_confidence_count
FROM
  `pyloto-prod.logs.atende_pyloto`
WHERE
  JSON_EXTRACT_SCALAR(json_payload, '$.metric_type') = 'confidence'
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY
  component, operation
ORDER BY
  avg_confidence ASC;

-- CloudWatch Logs Insights:
-- fields @timestamp, component, operation, confidence
-- | filter metric_type = "confidence"
-- | stats avg(confidence) as avg_confidence, count(*) as total by component, operation
-- | sort avg_confidence asc


-- ============================================================================
-- 3. HANDOFFS: Taxa e motivos de escalação para humano
-- ============================================================================

-- BigQuery:
SELECT
  JSON_EXTRACT_SCALAR(json_payload, '$.reason') AS handoff_reason,
  COUNT(*) AS handoff_count,
  ROUND(COUNT(*) / (SELECT COUNT(*) FROM `pyloto-prod.logs.atende_pyloto` WHERE JSON_EXTRACT_SCALAR(json_payload, '$.metric_type') = 'handoff' AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)) * 100, 2) AS percentage
FROM
  `pyloto-prod.logs.atende_pyloto`
WHERE
  JSON_EXTRACT_SCALAR(json_payload, '$.metric_type') = 'handoff'
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY
  handoff_reason
ORDER BY
  handoff_count DESC;

-- CloudWatch Logs Insights:
-- fields @timestamp, reason
-- | filter metric_type = "handoff"
-- | stats count(*) as handoff_count by reason
-- | sort handoff_count desc


-- ============================================================================
-- 4. TOKENS: Custo estimado por componente/operação
-- ============================================================================

-- BigQuery:
SELECT
  JSON_EXTRACT_SCALAR(json_payload, '$.component') AS component,
  JSON_EXTRACT_SCALAR(json_payload, '$.operation') AS operation,
  COUNT(*) AS total_calls,
  SUM(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.prompt_tokens') AS INT64)) AS total_prompt_tokens,
  SUM(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.completion_tokens') AS INT64)) AS total_completion_tokens,
  SUM(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.total_tokens') AS INT64)) AS total_tokens,
  AVG(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.total_tokens') AS INT64)) AS avg_tokens_per_call,
  -- Custo estimado (ajustar pricing conforme modelo)
  CASE component
    WHEN 'otto_agent' THEN SUM(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.total_tokens') AS INT64)) * 0.0025 / 1000  -- gpt-4o
    WHEN 'extraction_agent' THEN SUM(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.total_tokens') AS INT64)) * 0.00015 / 1000  -- gpt-4o-mini
    ELSE SUM(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.total_tokens') AS INT64)) * 0.0001 / 1000  -- default
  END AS estimated_cost_usd
FROM
  `pyloto-prod.logs.atende_pyloto`
WHERE
  JSON_EXTRACT_SCALAR(json_payload, '$.metric_type') = 'token_usage'
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY
  component, operation
ORDER BY
  total_tokens DESC;

-- CloudWatch Logs Insights:
-- fields @timestamp, component, operation, total_tokens
-- | filter metric_type = "token_usage"
-- | stats sum(total_tokens) as total_tokens, avg(total_tokens) as avg_tokens by component, operation
-- | sort total_tokens desc


-- ============================================================================
-- 5. CORRELAÇÃO: Latência vs Confidence (análise de qualidade)
-- ============================================================================

-- BigQuery:
WITH latencies AS (
  SELECT
    JSON_EXTRACT_SCALAR(json_payload, '$.correlation_id') AS correlation_id,
    CAST(JSON_EXTRACT_SCALAR(json_payload, '$.latency_ms') AS FLOAT64) AS latency_ms
  FROM
    `pyloto-prod.logs.atende_pyloto`
  WHERE
    JSON_EXTRACT_SCALAR(json_payload, '$.metric_type') = 'latency'
    AND JSON_EXTRACT_SCALAR(json_payload, '$.component') = 'otto_agent'
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
),
confidences AS (
  SELECT
    JSON_EXTRACT_SCALAR(json_payload, '$.correlation_id') AS correlation_id,
    CAST(JSON_EXTRACT_SCALAR(json_payload, '$.confidence') AS FLOAT64) AS confidence
  FROM
    `pyloto-prod.logs.atende_pyloto`
  WHERE
    JSON_EXTRACT_SCALAR(json_payload, '$.metric_type') = 'confidence'
    AND JSON_EXTRACT_SCALAR(json_payload, '$.component') = 'otto_agent'
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
)
SELECT
  CASE
    WHEN c.confidence < 0.5 THEN 'low (<0.5)'
    WHEN c.confidence BETWEEN 0.5 AND 0.7 THEN 'medium (0.5-0.7)'
    WHEN c.confidence BETWEEN 0.7 AND 0.85 THEN 'good (0.7-0.85)'
    ELSE 'high (>=0.85)'
  END AS confidence_bucket,
  COUNT(*) AS decision_count,
  AVG(l.latency_ms) AS avg_latency_ms,
  APPROX_QUANTILES(l.latency_ms, 100)[OFFSET(95)] AS p95_latency_ms
FROM
  latencies l
INNER JOIN
  confidences c
ON
  l.correlation_id = c.correlation_id
GROUP BY
  confidence_bucket
ORDER BY
  confidence_bucket;


-- ============================================================================
-- 6. SÉRIE TEMPORAL: Latência ao longo do tempo (últimas 24h)
-- ============================================================================

-- BigQuery:
SELECT
  TIMESTAMP_TRUNC(timestamp, HOUR) AS hour,
  JSON_EXTRACT_SCALAR(json_payload, '$.component') AS component,
  COUNT(*) AS operations,
  APPROX_QUANTILES(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.latency_ms') AS FLOAT64), 100)[OFFSET(50)] AS p50_latency_ms,
  APPROX_QUANTILES(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.latency_ms') AS FLOAT64), 100)[OFFSET(95)] AS p95_latency_ms
FROM
  `pyloto-prod.logs.atende_pyloto`
WHERE
  JSON_EXTRACT_SCALAR(json_payload, '$.metric_type') = 'latency'
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY
  hour, component
ORDER BY
  hour DESC, component;

-- CloudWatch Logs Insights:
-- fields @timestamp, component, latency_ms
-- | filter metric_type = "latency"
-- | stats pct(latency_ms, 50) as p50, pct(latency_ms, 95) as p95, count(*) as ops by bin(1h) as hour, component
-- | sort hour desc


-- ============================================================================
-- 7. HANDOFF RATE: Taxa de escalação ao longo do tempo
-- ============================================================================

-- BigQuery:
WITH total_decisions AS (
  SELECT
    TIMESTAMP_TRUNC(timestamp, HOUR) AS hour,
    COUNT(*) AS total
  FROM
    `pyloto-prod.logs.atende_pyloto`
  WHERE
    JSON_EXTRACT_SCALAR(json_payload, '$.metric_type') = 'confidence'
    AND JSON_EXTRACT_SCALAR(json_payload, '$.component') = 'otto_agent'
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  GROUP BY
    hour
),
handoffs AS (
  SELECT
    TIMESTAMP_TRUNC(timestamp, HOUR) AS hour,
    COUNT(*) AS handoff_count
  FROM
    `pyloto-prod.logs.atende_pyloto`
  WHERE
    JSON_EXTRACT_SCALAR(json_payload, '$.metric_type') = 'handoff'
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  GROUP BY
    hour
)
SELECT
  t.hour,
  COALESCE(h.handoff_count, 0) AS handoffs,
  t.total AS total_decisions,
  ROUND(COALESCE(h.handoff_count, 0) / t.total * 100, 2) AS handoff_rate_percent
FROM
  total_decisions t
LEFT JOIN
  handoffs h
ON
  t.hour = h.hour
ORDER BY
  t.hour DESC;


-- ============================================================================
-- 8. ALERTAS: Thresholds críticos (para uso em alerting)
-- ============================================================================

-- BigQuery:
-- Alerta 1: Latência P95 > 3000ms (últimos 15min)
SELECT
  'HIGH_LATENCY' AS alert_type,
  JSON_EXTRACT_SCALAR(json_payload, '$.component') AS component,
  APPROX_QUANTILES(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.latency_ms') AS FLOAT64), 100)[OFFSET(95)] AS p95_latency_ms
FROM
  `pyloto-prod.logs.atende_pyloto`
WHERE
  JSON_EXTRACT_SCALAR(json_payload, '$.metric_type') = 'latency'
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
GROUP BY
  component
HAVING
  p95_latency_ms > 3000;

-- Alerta 2: Taxa de handoff > 15% (últimos 15min)
WITH recent_decisions AS (
  SELECT COUNT(*) AS total
  FROM `pyloto-prod.logs.atende_pyloto`
  WHERE JSON_EXTRACT_SCALAR(json_payload, '$.metric_type') = 'confidence'
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
),
recent_handoffs AS (
  SELECT COUNT(*) AS handoffs
  FROM `pyloto-prod.logs.atende_pyloto`
  WHERE JSON_EXTRACT_SCALAR(json_payload, '$.metric_type') = 'handoff'
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
)
SELECT
  'HIGH_HANDOFF_RATE' AS alert_type,
  h.handoffs,
  d.total AS total_decisions,
  ROUND(h.handoffs / d.total * 100, 2) AS handoff_rate_percent
FROM
  recent_handoffs h,
  recent_decisions d
WHERE
  h.handoffs / d.total > 0.15;

-- Alerta 3: Confidence média < 0.7 (últimos 15min)
SELECT
  'LOW_CONFIDENCE' AS alert_type,
  JSON_EXTRACT_SCALAR(json_payload, '$.component') AS component,
  AVG(CAST(JSON_EXTRACT_SCALAR(json_payload, '$.confidence') AS FLOAT64)) AS avg_confidence
FROM
  `pyloto-prod.logs.atende_pyloto`
WHERE
  JSON_EXTRACT_SCALAR(json_payload, '$.metric_type') = 'confidence'
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
GROUP BY
  component
HAVING
  avg_confidence < 0.7;


-- ============================================================================
-- NOTAS DE USO:
-- ============================================================================
--
-- 1. Ajuste `pyloto-prod.logs.atende_pyloto` para o nome correto da tabela/log stream
-- 2. Adapte sintaxe para CloudWatch Logs Insights ou Elasticsearch conforme necessário
-- 3. Intervalos de tempo podem ser ajustados (24h, 7d, 30d)
-- 4. Thresholds de alertas devem ser calibrados com dados reais de produção
-- 5. Crie views materializadas (BigQuery) ou saved searches (CloudWatch) para dashboards
-- 6. Integre com ferramentas de visualização: Grafana, Looker, CloudWatch Dashboards
--
-- Para dashboards, recomenda-se:
-- - Painel 1: Latências (série temporal + histograma)
-- - Painel 2: Confidence (gauge + distribuição)
-- - Painel 3: Handoffs (taxa + motivos)
-- - Painel 4: Custos (tokens + estimativa USD)
-- - Painel 5: Alertas (status atual dos thresholds)
