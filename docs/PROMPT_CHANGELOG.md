# Changelog - Prompts e Contextos YAML

**Objetivo:** Rastrear mudanças em prompts, contextos e YAMLs de configuração de agentes IA, usando versionamento semântico.

**Formato:** Inspired by [Keep a Changelog](https://keepachangelog.com/) e [Semantic Versioning](https://semver.org/)

**Convenções de Versão:**

- **MAJOR (X.0.0):** Mudanças incompatíveis (alteram contrato do prompt/contexto de forma breaking)
- **MINOR (1.X.0):** Adição de novo conteúdo/funcionalidade sem quebrar compatibilidade
- **PATCH (1.0.X):** Correções de bugs, typos, ajustes de redação sem mudança semântica

**Estrutura de YAMLs:**
- `version`: Segue semver (ex: "1.2.3")
- `updated_at`: Data da última atualização (YYYY-MM-DD)

---

## [Unreleased]

Mudanças planejadas mas ainda não implementadas:

- Nenhuma mudança planejada no momento

---

## [1.0.0] - 2026-02-11

### Added - Novos Contextos (P1-1)

**ROI Hints por Vertente:**
- `src/ai/contexts/vertentes/automacao/roi_hints.yaml` (1.0.0)
  - Contexto de ROI para automação de atendimento
  - Cenários: 2-3 atendentes vs automação, payback 2-4 meses
  - Injection trigger: keywords de investimento/custo

- `src/ai/contexts/vertentes/saas/roi_hints.yaml` (1.0.0)
  - Contexto de ROI para SaaS Pyloto
  - Cenários: PME com 5-10 usuários, R$ 29/usuário/mês
  - Injection trigger: keywords de investimento/custo

- `src/ai/contexts/vertentes/sob_medida/roi_hints.yaml` (1.0.0)
  - Contexto de ROI para sistemas sob medida
  - Investimento: a partir de R$ 30k, payback 6-18 meses
  - Injection trigger: keywords de investimento/custo

- `src/ai/contexts/vertentes/trafego/roi_hints.yaml` (1.0.0)
  - Contexto de ROI para gestão de tráfego
  - Abordagem conservadora (não promete números específicos)
  - Foco: aumentar visibilidade e leads qualificados
  - Injection trigger: keywords de investimento/custo

- `src/ai/contexts/vertentes/entregas/roi_hints.yaml` (1.0.0)
  - Contexto de ROI para intermediação de entregas
  - Modelo: comissão por serviço intermediado
  - Foco: conveniência, segurança e qualidade
  - Injection trigger: keywords de investimento/custo

**Estrutura comum dos roi_hints.yaml:**
```yaml
version: "1.0.0"
updated_at: "2026-02-11"

metadata:
  context_type: "vertente_roi_hints"
  vertical_id: "{nome_vertente}"
  token_budget: 600
  priority: "medium"
  manual_injection: true
  persist: false
  min_confidence: 0.5
  injection_trigger:
    any_keywords: ["roi", "retorno", "payback", "investimento", "custo", ...]

prompt_injection: |
  ROI - {Nome da Vertente} (use com cautela, apenas se cliente perguntar):
  {Contexto específico da vertente com cenários e valores}
```

### Changed - Refatorações

**Micro-agents:**
- Refatorado `roi_agent()` para carregar YAML da vertente ao invés de gerar inline
- Removida lógica de `format_roi_inputs()` e template genérico `roi_hint_template.yaml`
- Novo padrão: todos os 3 micro-agents (objection, case, roi) carregam YAMLs específicos

---

## Contextos Core Existentes

Lista de contextos core (sem mudanças recentes, documentação para referência):

### Core System
- `src/ai/contexts/core/system_role.yaml` (1.0.0) — Papel do Otto como assistente B2B Pyloto
- `src/ai/contexts/core/mindset.yaml` (1.0.0) — Mindset conversacional: consultivo, empático, sem pressão
- `src/ai/contexts/core/guardrails.yaml` (1.0.0) — Proibições: promessas numéricas, dados sensíveis, tópicos off-topic
- `src/ai/contexts/core/sobre_pyloto.yaml` (1.0.0) — Informações sobre a empresa Pyloto

### Regras de Output
- `src/ai/contexts/regras/json_output.yaml` (1.0.0) — Formato estruturado de saída JSON

### Vertentes - Automação
- `src/ai/contexts/vertentes/automacao/core.yaml` (1.0.0) — Contexto base da vertente automação
- `src/ai/contexts/vertentes/automacao/faq.yaml` (1.0.0) — FAQ sobre automação
- `src/ai/contexts/vertentes/automacao/objections.yaml` (1.0.0) — Objeções comuns (preço, tempo, complexidade)
- `src/ai/contexts/vertentes/automacao/cases/index.yaml` (1.0.0) — Índice de casos de sucesso
- `src/ai/contexts/vertentes/automacao/cases/clinica.yaml` (1.0.0) — Caso: clínica médica
- `src/ai/contexts/vertentes/automacao/cases/ecommerce.yaml` (1.0.0) — Caso: e-commerce
- `src/ai/contexts/vertentes/automacao/cases/imobiliaria.yaml` (1.0.0) — Caso: imobiliária

### Vertentes - Sob Medida
- `src/ai/contexts/vertentes/sob_medida/core.yaml` (1.0.0) — Contexto base da vertente sob medida
- `src/ai/contexts/vertentes/sob_medida/objections.yaml` (1.0.0) — Objeções comuns
- `src/ai/contexts/vertentes/sob_medida/tech_stack.yaml` (1.0.0) — Stack tecnológico (Python, FastAPI, React)
- `src/ai/contexts/vertentes/sob_medida/cases/index.yaml` (1.0.0) — Índice de casos
- `src/ai/contexts/vertentes/sob_medida/cases/logistica.yaml` (1.0.0) — Caso: logística
- `src/ai/contexts/vertentes/sob_medida/cases/saude.yaml` (1.0.0) — Caso: saúde
- `src/ai/contexts/vertentes/sob_medida/cases/varejo.yaml` (1.0.0) — Caso: varejo

### Vertentes - Tráfego
- `src/ai/contexts/vertentes/trafego/core.yaml` (1.0.0) — Contexto base da vertente tráfego
- `src/ai/contexts/vertentes/trafego/objections.yaml` (1.0.0) — Objeções comuns
- `src/ai/contexts/vertentes/trafego/meta_ads.yaml` (1.0.0) — Contexto Meta Ads
- `src/ai/contexts/vertentes/trafego/seo_estrategia.yaml` (1.0.0) — Contexto SEO
- `src/ai/contexts/vertentes/trafego/cases/index.yaml` (1.0.0) — Índice de casos
- `src/ai/contexts/vertentes/trafego/cases/b2b_servicos.yaml` (1.0.0) — Caso: B2B serviços
- `src/ai/contexts/vertentes/trafego/cases/clinica_local.yaml` (1.0.0) — Caso: clínica local
- `src/ai/contexts/vertentes/trafego/cases/restaurante.yaml` (1.0.0) — Caso: restaurante

### Vertentes - SaaS
- `src/ai/contexts/vertentes/saas/core.yaml` (1.0.0) — Contexto base da vertente SaaS

### Vertentes - Entregas
- `src/ai/contexts/vertentes/entregas/core.yaml` (1.0.0) — Contexto base da vertente entregas

---

## Prompts de Agentes

Lista de prompts de agentes (sem mudanças recentes):

### Otto Agent
- `src/ai/prompts/yaml/otto_user_template.yaml` (1.0.0) — Template do user prompt para Otto

### Extraction Agent
- `src/ai/prompts/yaml/contact_card_extractor_system.yaml` (1.0.0) — System prompt do extrator
- `src/ai/prompts/yaml/contact_card_extractor_user_template.yaml` (1.0.0) — User template do extrator

### Deprecated
- ~~`src/ai/prompts/yaml/roi_hint_template.yaml`~~ — **REMOVIDO** (P1-1: substituído por YAMLs específicos por vertente)

---

## Como Atualizar Este Changelog

**Ao adicionar/modificar um YAML:**

1. Atualize o campo `version` no YAML seguindo semver
2. Atualize o campo `updated_at` no YAML (formato YYYY-MM-DD)
3. Adicione entrada neste changelog sob seção `[Unreleased]` ou nova versão
4. Categorize a mudança: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`

**Exemplo de entrada:**

```markdown
## [1.1.0] - 2026-02-15

### Changed
- `src/ai/contexts/vertentes/automacao/faq.yaml` (1.1.0)
  - Adicionada pergunta sobre integrações com CRMs
  - Atualizado preço base (de R$ 200-500/mês para R$ 300-600/mês)
```

**Quando versionar MAJOR (quebra compatibilidade):**
- Remoção de campos críticos usados por código
- Mudança de estrutura de metadados que quebra parsers
- Alteração de `injection_trigger` que muda completamente lógica de seleção

**Quando versionar MINOR (nova funcionalidade):**
- Adição de novo contexto/case
- Adição de novas keywords em `injection_trigger`
- Expansão de FAQ com novas perguntas

**Quando versionar PATCH (correções):**
- Correção de typos
- Ajustes de redação sem mudança semântica
- Correção de valores desatualizados (preços, contatos)

---

## Guidelines de Manutenção

1. **Evite breaking changes:** Sempre que possível, adicione ao invés de remover
2. **Documente deprecations:** Use seção `Deprecated` antes de remover na próxima versão MAJOR
3. **Teste após mudanças:** Execute testes de regressão após atualizar prompts críticos
4. **Review de contexto:** Mudanças em `core/` e `guardrails.yaml` requerem review de 2 pessoas
5. **Sincronize com código:** Se mudar estrutura de metadata, atualize parsers em `src/ai/` correspondentes

---

## Referências

- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- [README.md](./README.md) — Arquitetura do sistema
- [REGRAS_E_PADROES.md](./REGRAS_E_PADROES.md) — Padrões do repositório

---

**Última atualização:** 2026-02-11
**Mantido por:** Equipe Atende_Pyloto
