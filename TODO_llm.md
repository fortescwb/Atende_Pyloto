# TODO — Aprimoramento do Contexto, Humanização e Persistência do LLM

> **Objetivo:** Melhorar a qualidade das respostas do Otto (assistente virtual) através de contexto enriquecido, histórico de conversa persistente, informações institucionais e prompts humanizados.
>
> **Data de criação:** 03/02/2026  
> **Responsável:** Equipe Pyloto  
> **Status:** � Em execução (P0 ✅, P1 parcial)

---

## Sumário

1. [Diagnóstico Atual](#1-diagnóstico-atual)
2. [Arquitetura de Contexto e Persistência](#2-arquitetura-de-contexto-e-persistência)
3. [Tarefas P0 — Críticas (Pré-produção)](#3-tarefas-p0--críticas-pré-produção)
4. [Tarefas P1 — Estruturais e Persistência (Sprint Atual)](#4-tarefas-p1--estruturais-e-persistência-sprint-atual)
5. [Tarefas P2 — Integrações (Próximos PRs)](#5-tarefas-p2--integrações-próximos-prs)
6. [Especificação: Arquivo de Contexto Institucional](#6-especificação-arquivo-de-contexto-institucional)
7. [Especificação: Persistência de Conversas (Firestore)](#7-especificação-persistência-de-conversas-firestore)
8. [Especificação: Prompts Atualizados](#8-especificação-prompts-atualizados)
9. [Critérios de Aceite](#9-critérios-de-aceite)
10. [Checklist de Validação](#10-checklist-de-validação)

---

## 1) Diagnóstico Atual

### Problemas Identificados

| # | Problema | Evidência | Impacto |
|---|----------|-----------|---------|
| 1 | **Histórico NÃO é passado ao ResponseAgent** | `orchestrator.py:137` — `detected_intent="general"` hardcoded | Modelo trata cada mensagem como primeira |
| 2 | **session_context é apenas técnico** | Contém apenas `tenant_id`, `vertente`, `turn_count` | Modelo não sabe nome do lead nem intenção |
| 3 | **Modelo não conhece suas limitações** | `system_role.py` não menciona o que NÃO pode fazer | Modelo "agenda" reuniões sem acesso real |
| 4 | **Ausência de informações institucionais** | Não há endereço, horário, preços, etc. | Modelo responde "não posso fornecer endereço" |
| 5 | **Prompts sem exemplos (few-shot)** | Todos prompts são instrucionais | Respostas robóticas ("Prezada(o)") |
| 6 | **Histórico é `list[str]` sem estrutura** | `models.py:55` | Não distingue user/assistant |
| 7 | **Histórico é volátil (Redis TTL)** | `redis_session_store.py` — TTL 2h | Após sessão expirar, histórico é perdido |
| 8 | **Sem persistência permanente de conversas** | Não existe `ConversationStore` | Impossível consultar conversas antigas |

### Conversa de Teste (Evidência)

```trecho de conversa real
Usuário: pode ser na sexta feira dia 06/02/2026 às 14 horas?
Otto: Prezada(o), informo que a data solicitada [...] está disponível.
      ⚠️ Agendou sem perguntar nome, sem verificar agenda real

Usuário: só me confirma o endereço de vocês?
Otto: Não podemos fornecer informações de endereço.
      ⚠️ Deveria ter essa informação disponível
```

---

## 2) Arquitetura de Contexto e Persistência

### 2.1 — Visão Geral do Contexto

```arquitetura
┌─────────────────────────────────────────────────────────────────────┐
│                    CONTEXTO ENRIQUECIDO DO LLM                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 1. CONTEXTO INSTITUCIONAL (estático, carregado do YAML)    │   │
│  │    - Informações da empresa (endereço, telefone, horário)  │   │
│  │    - Serviços oferecidos e faixas de preço                 │   │
│  │    - Clientes/cases de sucesso                             │   │
│  │    - Modelos de parceria                                   │   │
│  │    - Links úteis (agendamento, site, redes sociais)        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 2. CONTEXTO DE SESSÃO (dinâmico, por conversa)             │   │
│  │    - Nome do lead (quando coletado)                        │   │
│  │    - Email/telefone (quando coletado)                      │   │
│  │    - Intenção principal detectada                          │   │
│  │    - Dados coletados durante a conversa                    │   │
│  │    - Ações pendentes                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 3. HISTÓRICO DE CONVERSA (estruturado + PERSISTIDO)        │   │
│  │    - Últimas N mensagens com role (user/assistant)         │   │
│  │    - Intenção detectada por turno                          │   │
│  │    - Timestamps                                            │   │
│  │    - DUAL-WRITE: Redis (sessão) + Firestore (permanente)   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 4. CAPACIDADES E LIMITAÇÕES (dinâmico por integração)      │   │
│  │    - ✅ O que o modelo PODE fazer                          │   │
│  │    - ❌ O que o modelo NÃO PODE fazer                      │   │
│  │    - 🔜 O que estará disponível em breve                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 — Fluxo de Persistência de Conversas

```fluxo
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FLUXO DE PERSISTÊNCIA                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MENSAGEM RECEBIDA                                                          │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        DUAL-WRITE                                   │   │
│  │  ┌─────────────────┐           ┌─────────────────────────────────┐ │   │
│  │  │     REDIS       │           │          FIRESTORE              │ │   │
│  │  │  (sessão ativa) │           │       (permanente)              │ │   │
│  │  │                 │           │                                 │ │   │
│  │  │  • TTL: 2h      │     +     │  • Collection: conversations    │ │   │
│  │  │  • Sessão atual │           │  • TTL: ∞ (ou retenção LGPD)    │ │   │
│  │  │  • Histórico N  │           │  • Todas as mensagens           │ │   │
│  │  │  • LeadProfile  │           │  • LeadProfile                  │ │   │
│  │  └─────────────────┘           └─────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  NOVA SESSÃO (usuário volta após dias/semanas)                              │
│       │                                                                     │
│       ▼                                                                     │
│  1. Busca sessão no Redis → NÃO encontra (expirou)                          │
│  2. Busca lead no Firestore por phone_hash → ENCONTRA!                      │
│  3. Carrega últimas N mensagens do Firestore                                │
│  4. Reconstrói LeadProfile (nome, intent, dados coletados)                  │
│  5. Otto: "Oi Maria! Faz tempo que não conversamos. Como posso ajudar?"     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 — Infraestrutura Existente (Aproveitada)

| Componente | Status | Arquivo |
|------------|--------|---------|
| **Firestore Client** | ✅ Existe | `src/app/bootstrap/clients.py:94-104` |
| **Redis Session Store** | ✅ Existe | `src/app/infra/stores/redis_session_store.py` |
| **Firestore Audit Store** | ✅ Existe | `src/app/infra/stores/firestore_audit_store.py` |
| **DecisionAuditStoreProtocol** | ✅ Existe | `src/app/protocols/decision_audit_store.py` |
| **Conversation Store** | ✅ Criado | `src/app/infra/stores/firestore_conversation_store.py` |
| **ConversationStoreProtocol** | ✅ Criado | `src/app/protocols/conversation_store.py` |
| **LeadExtractor** | ✅ Criado | `src/ai/services/lead_extractor.py` |
| **SessionManager (dual-write)** | ✅ Atualizado | `src/app/sessions/manager.py` |

---

## 3) Tarefas P0 — Críticas (Pré-produção)

> ⏱️ Estimativa: 1-2 dias  
> 🎯 Objetivo: Corrigir problemas mais graves que afetam qualidade básica  
> ✅ **STATUS: CONCLUÍDO em 04/02/2026**

### P0.1 — Passar histórico de conversa para ResponseAgent

- [x] **Arquivo:** `src/ai/services/orchestrator.py`
- [x] **Mudança:** Incluir `session_history` no request do `_generate_response()`
- [x] **Impacto:** Modelo terá contexto das mensagens anteriores

```python
# ANTES (linha 132-142)
async def _generate_response(
    self,
    user_input: str,
    current_state: str,
    session_context: dict[str, str] | None,
) -> ResponseGenerationResult:

# DEPOIS
async def _generate_response(
    self,
    user_input: str,
    current_state: str,
    session_context: dict[str, str] | None,
    session_history: list[str] | None = None,  # NOVO
) -> ResponseGenerationResult:
```

### P0.2 — Atualizar template do ResponseAgent para incluir histórico

- [x] **Arquivo:** `src/ai/prompts/response_agent_prompt.py`
- [x] **Mudança:** Adicionar campo `{conversation_history}` no template

```python
RESPONSE_AGENT_USER_TEMPLATE = """Intenção detectada: {detected_intent}
Estado atual: {current_state}
Próximo estado: {next_state}

Histórico da conversa:
{conversation_history}

Mensagem atual do usuário: {user_input}
Contexto da sessão: {session_context}

Gere 3 candidatos de resposta. Responda APENAS em JSON válido."""
```

### P0.3 — Usar detected_intent real ao invés de hardcoded

- [x] **Arquivo:** `src/ai/services/orchestrator.py`
- [x] **Mudança:** Substituir `"general"` por `state_result.detected_intent`

```python
# ANTES
detected_intent="general",

# DEPOIS
detected_intent=state_result.detected_intent or "general",
```

### P0.4 — Criar arquivo de contexto institucional

- [x] **Arquivo:** `src/ai/config/institutional_context.yaml`
- [x] **Conteúdo:** YAML com empresa, contato, endereço, horários, vertentes, faixas de preço

### P0.5 — Expandir SYSTEM_ROLE com limitações e comportamento

- [x] **Arquivo:** `src/ai/prompts/system_role.py`
- [x] **Mudança:** Incluir capacidades, limitações e tom esperado
- [x] **Conteúdo:** SYSTEM_ROLE expandido com regras do Otto

---

## 4) Tarefas P1 — Estruturais e Persistência (Sprint Atual)

> ⏱️ Estimativa: 5-7 dias  
> 🎯 Objetivo: Estruturar dados do lead, persistir conversas e melhorar qualidade das respostas  
> � **STATUS: CONCLUÍDO em 04/02/2026**

### P1.1 — Criar estrutura LeadProfile no SessionContext

- [x] **Arquivo:** `src/app/sessions/models.py`
- [x] **Mudança:** Adicionado dataclass `LeadProfile`

```python
@dataclass(slots=True)
class LeadProfile:
    """Perfil do lead coletado durante a conversa."""
    
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    primary_intent: str | None = None
    collected_data: dict[str, Any] = field(default_factory=dict)
    pending_questions: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SessionContext:
    tenant_id: str = ""
    vertente: str = "geral"
    rules: dict[str, Any] = field(default_factory=dict)
    limits: dict[str, int] = field(default_factory=dict)
    lead_profile: LeadProfile | None = None  # NOVO
```

### P1.2 — Estruturar histórico com role e timestamp

- [x] **Arquivo:** `src/app/sessions/models.py`
- [x] **Mudança:** Adicionados `HistoryRole` enum e `HistoryEntry` dataclass

```python
@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """Entrada estruturada do histórico de conversa."""
    
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    intent: str | None = None
    
    def to_prompt_format(self) -> str:
        """Formata para uso em prompts."""
        role_label = "Usuário" if self.role == "user" else "Otto"
        return f"{role_label}: {self.content}"
```

### P1.3 — Criar loader para contexto institucional

- [x] **Arquivo:** `src/ai/config/institutional_loader.py`
- [x] **Função:** `load_institutional_context()`, `get_institutional_prompt_section()`, helpers

```python
from functools import lru_cache
import yaml

@lru_cache(maxsize=1)
def load_institutional_context() -> dict[str, Any]:
    """Carrega contexto institucional do YAML (cached)."""
    path = Path(__file__).parent / "institutional_context.yaml"
    with open(path) as f:
        return yaml.safe_load(f)

def get_institutional_prompt_section() -> str:
    """Retorna seção formatada para inserir em prompts."""
    ctx = load_institutional_context()
    # Formata para prompt...
```

### P1.4 — Adicionar few-shot examples nos prompts

- [x] **Arquivo:** `src/ai/prompts/response_agent_prompt.py`
- [x] **Mudança:** Adicionados 3 exemplos de conversas humanizadas (saudação, serviços, orçamento)

### P1.5 — Implementar extração automática de dados do lead

- [x] **Arquivo:** `src/ai/services/lead_extractor.py` (criado)
- [x] **Função:** `extract_name()`, `extract_email()`, `extract_phone()`, `extract_lead_data()`
- [x] **Testes:** `tests/test_ai/test_lead_extractor.py` (19 testes)

### P1.6 — Atualizar serialização de sessão para novos campos

- [x] **Arquivo:** `src/app/sessions/models.py`
- [x] **Métodos:** `to_dict()` e `from_dict()` atualizados com suporte a `HistoryEntry`

### P1.7 — Criar protocolo e store para persistência de conversas (Firestore)

- [x] **Arquivo:** `src/app/protocols/conversation_store.py` (criado)
- [x] **Arquivo:** `src/app/infra/stores/firestore_conversation_store.py` (criado)
- [x] **Descrição:** Protocol com `append_message()`, `get_messages()`, `upsert_lead()`, `get_lead()`
- [x] **Testes:** `tests/app/protocols/test_conversation_store.py` (8 testes)

```python
# src/app/protocols/conversation_store.py
class ConversationStoreProtocol(ABC):
    """Contrato para armazenamento permanente de conversas."""

    @abstractmethod
    async def append_message(
        self, 
        phone_hash: str, 
        message: HistoryEntry,
        session_id: str,
    ) -> None:
        """Persiste mensagem individual."""

    @abstractmethod
    async def get_recent_messages(
        self, 
        phone_hash: str, 
        limit: int = 20,
    ) -> list[HistoryEntry]:
        """Recupera últimas N mensagens do lead."""

    @abstractmethod
    async def get_lead_profile(self, phone_hash: str) -> LeadProfile | None:
        """Recupera perfil do lead (se existir)."""

    @abstractmethod
    async def save_lead_profile(self, phone_hash: str, profile: LeadProfile) -> None:
        """Persiste/atualiza perfil do lead."""
```

### P1.8 — Criar Firestore Conversation Store (implementação)

- [x] **Arquivo:** `src/app/infra/stores/firestore_conversation_store.py` (criado)
- [x] **Collections Firestore:**
  - `conversations/{tenant_id}_{phone_hash}/messages/{msg_id}` — mensagens individuais
  - `leads/{tenant_id}_{phone_hash}` — perfil do lead
- [x] **Campos por mensagem:**
  - `role`: "user" | "assistant"
  - `content`: texto (sanitizado, sem PII sensível)
  - `timestamp`: datetime
  - `channel`: "whatsapp" | "instagram" | etc.
  - `detected_intent`: intenção detectada (opcional)
  - `metadata`: dados extras

```python
# Estrutura no Firestore
conversations/
  {phone_hash}/
    messages/
      {timestamp}_{uuid}/
        role: "user"
        content: "Quero saber sobre sistemas"
        timestamp: 2026-02-03T16:49:00Z
        session_id: "sess_abc123"
        intent: "PRICING_INQUIRY"
        channel: "whatsapp"
        
leads/
  {phone_hash}/
    name: "Maria"
    email: "maria@example.com"
    primary_intent: "sob_medida"
    first_contact: 2026-02-03T16:49:00Z
    last_contact: 2026-02-03T17:30:00Z
    total_sessions: 3
    collected_data: {...}
```

### P1.9 — Implementar dual-write (Redis + Firestore)

- [x] **Arquivo:** `src/app/sessions/manager.py`
- [x] **Mudança:** Método `add_message()` com dual-write pattern
- [x] **Padrão:** Write-through (Firestore async via `asyncio.create_task`, não bloqueia fluxo)

```python
async def add_message(
    self,
    session: Session,
    content: str,
    role: HistoryRole,
    *,
    detected_intent: str | None = None,
    channel: str = "whatsapp",
    message_id: str | None = None,
) -> None:
    """Adiciona mensagem à sessão com dual-write."""
    # 1. Adiciona ao histórico local (Redis)
    session.add_to_history(content, role, detected_intent)
    await self.save(session)
    
    # 2. Dual-write para Firestore (async, fire-and-forget)
    if self._conversation_store is not None:
        asyncio.create_task(  # noqa: RUF006
            self._persist_message_to_firestore(...)
        )
```

### P1.10 — Recuperar histórico do Firestore ao criar nova sessão

- [x] **Arquivo:** `src/app/sessions/manager.py`
- [x] **Mudança:** Em `resolve_or_create()`, recuperar histórico do Firestore quando sessão não existe no Redis
- [x] **Método:** `_recover_from_firestore()` busca lead e mensagens em paralelo

```python
async def resolve_or_create(
    self,
    sender_id: str,
    tenant_id: str = "",
    vertente: str = "geral",
    channel: str = "whatsapp",
) -> Session:
    """Resolve sessão existente ou cria nova com recovery do Firestore."""
    # 1. Tenta carregar do Redis (sessão ativa)
    existing = await self._store.load_async(lookup_key)
    if existing is not None:
        return Session.from_dict(existing)

    # 2. Sessão não existe no Redis — buscar histórico no Firestore
    return await self._create_with_recovery(...)
```

### P1.11 — Criar testes para persistência de conversas

- [x] **Arquivo:** `tests/app/sessions/test_session_manager.py` (criado)
- [x] **Cobertura (11 testes):**
  - Criação de sessão
  - Resolução de sessão existente
  - Dual-write salva no Redis e dispara task para Firestore
  - add_message funciona sem ConversationStore
  - Recovery carrega LeadProfile do Firestore
  - Recovery carrega histórico de mensagens
  - Recovery trata erro do Firestore graciosamente
  - Sem recovery quando não há ConversationStore
  - update_lead_profile persiste no Firestore
  - close session remove do Redis

---

## 5) Tarefas P2 — Integrações (Próximos PRs)

> ⏱️ Estimativa: 5-10 dias  
> 🎯 Objetivo: Integrar com Google Agenda e outros sistemas

### P2.1 — Integração Google Calendar (PR específico)

- [ ] **Criar:** `src/app/infra/calendar/google_calendar_client.py`
- [ ] **Criar:** `src/ai/tools/calendar_tools.py` — funções disponíveis para o LLM
- [ ] **Atualizar:** Prompts para indicar que TEM acesso à agenda
- [ ] **Implementar:** Verificação de disponibilidade
- [ ] **Implementar:** Criação de eventos

### P2.2 — Sistema de coleta estruturada de dados

- [ ] **Criar:** Fluxo de perguntas obrigatórias por tipo de intenção
- [ ] **Exemplo:** Agendamento requer: nome, email, assunto, horário preferido

### P2.3 — Integração com CRM para persistência de leads

- [ ] **Criar:** Adapter para salvar `LeadProfile` no CRM
- [ ] **Criar:** Recuperar dados de leads recorrentes

### P2.4 — Suporte a múltiplos canais

- [ ] **Adaptar:** Contexto institucional por canal
- [ ] **Adaptar:** Tom de resposta por canal (WhatsApp vs Email vs Instagram)

---

## 6) Especificação: Arquivo de Contexto Institucional

> **Caminho:** `src/ai/config/institutional_context.yaml`

```yaml
# ============================================================================
# CONTEXTO INSTITUCIONAL PYLOTO
# ============================================================================
# Este arquivo contém informações públicas sobre a empresa que podem ser
# compartilhadas pelo assistente virtual Otto.
#
# ⚠️ NÃO inclua informações sensíveis (senhas, tokens, dados internos)
# ⚠️ Mantenha preços como "faixas" ou "a partir de", não valores exatos
# ============================================================================

empresa:
  nome: "Pyloto"
  nome_completo: "Pyloto Tecnologia e Soluções Digitais"
  slogan: "Tecnologia que conecta pessoas e negócios"
  
  contato:
    telefone: "(XX) XXXX-XXXX"  # TODO: Preencher
    whatsapp: "(XX) XXXXX-XXXX"  # TODO: Preencher
    email_comercial: "comercial@pyloto.com.br"
    email_suporte: "suporte@pyloto.com.br"
    site: "https://pyloto.com.br"
    
  endereco:
    logradouro: "Rua XXXXX, 000"  # TODO: Preencher
    complemento: "Sala 00"
    bairro: "XXXXX"
    cidade: "XXXXX"
    estado: "XX"
    cep: "00000-000"
    # Para reuniões presenciais, confirmar endereço com lead
    
  redes_sociais:
    instagram: "@pyloto"
    linkedin: "company/pyloto"
    
  horarios:
    atendimento_humano:
      dias: "Segunda a Sexta"
      horario: "09:00 às 18:00"
      fuso: "America/Sao_Paulo"
    atendimento_otto:
      disponibilidade: "24 horas por dia, 7 dias por semana"
    reunioes:
      dias: "Segunda a Sexta"
      horario: "09:00 às 17:00"
      duracao_padrao: "30 minutos"
      link_agendamento: "https://calendly.com/pyloto"  # TODO: Confirmar

servicos:
  - id: "intermediacao"
    nome: "Pyloto Entregas/Serviços"
    descricao: "Plataforma de intermediação entre solicitantes e prestadores de serviço"
    segmentos:
      - "Entregas rápidas"
      - "Serviços gerais"
      - "Freelancers"
    preco_referencia: "Sob consulta (modelo de comissão por transação)"
    
  - id: "saas"
    nome: "SaaS Pyloto"
    descricao: "Sistema adaptável para gestão empresarial, personalizável para diversos nichos"
    segmentos:
      - "Clínicas e consultórios"
      - "Escritórios de advocacia"
      - "Academias e estúdios"
      - "Restaurantes e delivery"
      - "Salões de beleza"
    preco_referencia: "A partir de R$ XXX/mês"  # TODO: Definir
    
  - id: "trafego"
    nome: "Gestão de Tráfego e Perfis"
    descricao: "Gestão profissional de redes sociais e campanhas de tráfego pago"
    inclui:
      - "Gestão de Instagram/Facebook"
      - "Campanhas Google Ads"
      - "Relatórios mensais"
    preco_referencia: "A partir de R$ XXX/mês"  # TODO: Definir
    
  - id: "sob_medida"
    nome: "Sistemas Sob Medida"
    descricao: "Desenvolvimento de sistemas e sites personalizados para necessidades específicas"
    inclui:
      - "Análise de requisitos"
      - "Desenvolvimento exclusivo"
      - "Suporte e manutenção"
      - "Treinamento da equipe"
    preco_referencia: "Orçamento sob consulta (projetos a partir de R$ X.XXX)"  # TODO: Definir
    prazo_medio: "4 a 12 semanas dependendo da complexidade"

parcerias:
  modelos:
    - tipo: "Indicação"
      descricao: "Indique clientes e ganhe comissão por projeto fechado"
      comissao: "X% sobre o valor do projeto"  # TODO: Definir
      
    - tipo: "Revenda"
      descricao: "Revenda nosso SaaS com sua marca (white-label)"
      requisitos: "Mínimo de X clientes ativos"
      
    - tipo: "Tecnológica"
      descricao: "Integração de sistemas e APIs"

cases_sucesso:
  # Listar apenas cases públicos autorizados
  - cliente: "Exemplo Empresa ABC"
    segmento: "Delivery"
    resultado: "Aumento de 40% nas entregas"
    depoimento: "A Pyloto transformou nossa operação..."
    # TODO: Adicionar cases reais autorizados

faq:
  - pergunta: "Qual o prazo para desenvolver um sistema?"
    resposta: "O prazo varia de 4 a 12 semanas dependendo da complexidade. Após a análise inicial, fornecemos um cronograma detalhado."
    
  - pergunta: "Vocês fazem manutenção após a entrega?"
    resposta: "Sim, oferecemos planos de suporte e manutenção mensal para garantir que seu sistema esteja sempre atualizado e funcionando."
    
  - pergunta: "Posso testar o SaaS antes de contratar?"
    resposta: "Sim, oferecemos um período de teste gratuito de X dias para você conhecer a plataforma."
    
  - pergunta: "Vocês atendem todo o Brasil?"
    resposta: "Sim, atendemos clientes em todo o Brasil. Reuniões podem ser presenciais (na região de XXXXX) ou por videoconferência."

# Capacidades atuais do Otto (assistente virtual)
capacidades_otto:
  pode_fazer:
    - "Responder dúvidas sobre serviços e preços"
    - "Explicar modelos de parceria"
    - "Coletar informações do lead (nome, email, necessidade)"
    - "Direcionar para canais de atendimento humano"
    - "Fornecer informações de contato e endereço"
    
  nao_pode_fazer:
    - "Agendar reuniões diretamente na agenda (em breve!)"
    - "Fornecer orçamentos exatos (apenas faixas de preço)"
    - "Acessar dados de clientes existentes"
    - "Processar pagamentos"
    - "Dar suporte técnico avançado"
    
  em_breve:
    - "Integração com Google Agenda para agendamento real"
    - "Consulta de status de projetos"
    - "Abertura de tickets de suporte"
```

---

## 7) Especificação: Persistência de Conversas (Firestore)

> **Objetivo:** Armazenar permanentemente todas as conversas para consulta futura, continuidade cross-sessão e análise de dados.

### 7.1 — Estrutura de Collections no Firestore

```
firestore/
│
├── conversations/                     # Histórico de mensagens por lead
│   └── {phone_hash}/                  # Documento por lead (hash do telefone)
│       └── messages/                  # Subcollection de mensagens
│           └── {timestamp}_{uuid}/    # Documento por mensagem
│               ├── role: "user" | "assistant"
│               ├── content: string    # Texto sanitizado (sem PII sensível)
│               ├── timestamp: datetime
│               ├── session_id: string # Para agrupar mensagens da mesma sessão
│               ├── intent: string?    # Intenção detectada (opcional)
│               ├── channel: string    # "whatsapp" | "instagram" | "web"
│               └── metadata: map      # Dados extras (opcional)
│
├── leads/                             # Perfis de leads
│   └── {phone_hash}/                  # Documento por lead
│       ├── name: string?
│       ├── email: string?
│       ├── company: string?
│       ├── primary_intent: string?
│       ├── first_contact: datetime    # Primeira interação
│       ├── last_contact: datetime     # Última interação
│       ├── total_sessions: number     # Quantas sessões diferentes
│       ├── total_messages: number     # Total de mensagens trocadas
│       ├── collected_data: map        # Dados coletados durante conversas
│       ├── tags: array<string>        # Tags para segmentação
│       └── channel_first_contact: string  # Canal do primeiro contato
│
└── decision_audit/                    # Já existente (decisões de IA)
    └── {tenant}_{date}_{session}_{ts}/
```

### 7.2 — Políticas de Retenção (LGPD)

| Tipo de Dado | Retenção | Justificativa |
|--------------|----------|---------------|
| Mensagens | 2 anos | Histórico comercial + suporte |
| LeadProfile | Indefinido (até opt-out) | CRM |
| Dados sensíveis (email/phone) | Nunca no content | Apenas hash como chave |

### 7.3 — Considerações de Segurança

- **phone_hash:** SHA256 do telefone — nunca armazenar telefone em texto claro
- **content:** Mensagens passam por `sanitize_pii()` antes de persistir
- **Índices:** Criar índice composto em `phone_hash + timestamp` para queries eficientes
- **Firestore Rules:** Restringir acesso apenas ao service account do Cloud Run

### 7.4 — Queries Comuns

```python
# 1. Últimas N mensagens de um lead
db.collection("conversations").document(phone_hash) \
  .collection("messages") \
  .order_by("timestamp", direction=DESCENDING) \
  .limit(20)

# 2. Perfil do lead
db.collection("leads").document(phone_hash).get()

# 3. Leads que conversaram nos últimos 7 dias (para follow-up)
db.collection("leads") \
  .where("last_contact", ">=", seven_days_ago) \
  .order_by("last_contact", direction=DESCENDING)

# 4. Todas as mensagens de uma sessão específica
db.collection("conversations").document(phone_hash) \
  .collection("messages") \
  .where("session_id", "==", session_id) \
  .order_by("timestamp")
```

---

## 8) Especificação: Prompts Atualizados

### 7.1 — System Role Atualizado

> **Arquivo:** `src/ai/prompts/system_role.py`

```python
"""System role compartilhado por todos os agentes LLM.

Define a persona e regras base do assistente Otto.
Carrega contexto institucional do YAML.
"""

from __future__ import annotations

from ai.config.institutional_loader import get_institutional_summary

# Contexto institucional é carregado do YAML
_INSTITUTIONAL = get_institutional_summary()

SYSTEM_ROLE = f"""Você é Otto, o assistente virtual da Pyloto. Você é simpático, prestativo e fala de forma natural — como um colega de trabalho, não como um robô.

## Sobre a Pyloto
{_INSTITUTIONAL['empresa_resumo']}

## Serviços que oferecemos
{_INSTITUTIONAL['servicos_resumo']}

## Informações de contato
{_INSTITUTIONAL['contato_resumo']}

## O que você PODE fazer
- Responder dúvidas sobre nossos serviços
- Explicar faixas de preço e modelos de parceria
- Coletar informações do lead (nome, email, telefone, necessidade)
- Fornecer endereço e informações de contato
- Sugerir que o lead agende uma reunião (enviar link do Calendly)

## O que você NÃO PODE fazer (ainda)
- ❌ Agendar reuniões diretamente — você não tem acesso à agenda real
- ❌ Dar orçamentos exatos — apenas faixas de preço
- ❌ Acessar dados de clientes existentes
- ❌ Processar pagamentos ou contratos

## Como você deve se comportar
1. **Seja humano:** Use linguagem natural, evite "Prezado(a)" e formalidades excessivas
2. **Seja proativo:** Pergunte o nome do lead se ainda não souber
3. **Seja honesto:** Se não souber algo, diga "Não tenho essa informação agora, mas posso anotar para a equipe retornar"
4. **Seja útil:** Sempre ofereça próximos passos claros
5. **Seja breve:** Respostas concisas, máximo 3 parágrafos

## Exemplos de tom adequado
❌ "Prezado(a), agradeço pelo seu contato. Informo que..."
✅ "Oi! Que bom que entrou em contato. Como posso te ajudar?"

❌ "Não podemos fornecer informações de endereço."
✅ "Nosso escritório fica na Rua XXX, 000 - Centro. Quer marcar uma visita?"

## Regras de segurança
- Nunca exponha CPF, CNPJ, senhas ou tokens
- Não invente informações que não estão neste contexto
- Sinalize quando precisar de ajuda humana
"""

# Template para inserir dados dinâmicos da sessão
DYNAMIC_CONTEXT_TEMPLATE = """
## Dados desta conversa
- Nome do lead: {lead_name}
- Intenção principal: {primary_intent}
- Turno atual: {turn_count}
- Dados já coletados: {collected_data}
"""
```

### 7.2 — Response Agent com Histórico e Few-Shot

> **Arquivo:** `src/ai/prompts/response_agent_prompt.py`

```python
RESPONSE_AGENT_USER_TEMPLATE = """## Contexto da conversa
Intenção detectada: {detected_intent}
Estado atual: {current_state}
Próximo estado: {next_state}

## Histórico recente
{conversation_history}

## Mensagem atual do usuário
{user_input}

## Dados do lead
{session_context}

## Instruções
Gere EXATAMENTE 3 candidatos de resposta com tons diferentes.
Lembre-se: você está continuando uma conversa, não iniciando uma nova.

## Exemplos de boas respostas

Exemplo 1 (casual):
Usuário perguntou sobre sistemas sob medida para advocacia.
"Legal! Sistemas para escritórios de advocacia são bem procurados. A gente já fez alguns projetos assim — gestão de processos, controle de prazos, esse tipo de coisa. Pra eu entender melhor, qual o tamanho do escritório? Quantos advogados mais ou menos?"

Exemplo 2 (empático):
Usuário quer agendar uma reunião.
"Perfeito, vamos marcar sim! Pra facilitar, me passa seu email que envio um convite com as opções de horário. Pode ser?"

Exemplo 3 (formal):
Lead corporativo pedindo informações.
"Temos experiência em projetos corporativos de diversos portes. Posso enviar um material detalhado para seu email? Assim você consegue avaliar com calma e compartilhar com sua equipe."

Responda APENAS em JSON válido."""
```

---

## 9) Critérios de Aceite

### Funcionalidade

- [ ] Otto usa o nome do lead após ser informado
- [ ] Otto lembra o que foi discutido anteriormente na mesma sessão
- [ ] Otto informa corretamente o endereço quando perguntado
- [ ] Otto NÃO afirma ter agendado reunião (até integração P2.1)
- [ ] Otto sugere link do Calendly para agendamento
- [ ] Otto pergunta nome/email quando necessário para próximo passo
- [ ] Respostas têm tom natural, não robótico

### Técnicos

- [x] Histórico é passado para ResponseAgent
- [x] Contexto institucional é carregado do YAML
- [x] LeadProfile definido na sessão
- [x] HistoryEntry estruturado com role/timestamp
- [x] LeadExtractor implementado (regex)
- [x] ConversationStoreProtocol criado
- [x] FirestoreConversationStore implementado
- [ ] **Mensagens são persistidas no Firestore (dual-write)** — pendente P1.9
- [ ] **Nova sessão recupera histórico do Firestore quando Redis expira** — pendente P1.10
- [x] Testes unitários passam (458/458)
- [x] Cobertura de código mantida ≥80%
- [x] Nenhum PII em logs

---

## 10) Checklist de Validação

### Pré-deploy

- [ ] Rodar `pytest` — todos testes passam
- [ ] Rodar `ruff check src/` — sem erros
- [ ] Verificar logs não contêm PII
- [ ] Testar conversa completa em staging
- [ ] **Verificar que mensagens aparecem no Firestore**

### Pós-deploy

- [ ] Simular conversa: saudação → dúvida → agendamento → despedida
- [ ] Verificar que Otto lembra o nome após informado
- [ ] Verificar que Otto fornece endereço quando perguntado
- [ ] Verificar que Otto NÃO confirma agendamento (apenas sugere link)
- [ ] **Simular sessão expirada: esperar 2h+ e iniciar nova conversa**
- [ ] **Verificar que Otto lembra o nome mesmo após sessão expirar**
- [ ] Monitorar logs de erro por 24h

### Cenários de Teste

```
Cenário 1: Coleta de nome
  Usuário: "Oi, quero saber sobre sistemas"
  Otto: "Oi! Tudo bem? Claro, posso te ajudar com isso. Qual seu nome?"
  Usuário: "Maria"
  Otto: "Prazer, Maria! Então me conta, que tipo de sistema você precisa?"
  ✅ Otto deve usar "Maria" nas próximas mensagens

Cenário 2: Endereço
  Usuário: "Qual o endereço de vocês?"
  Otto: "Nosso escritório fica na [ENDEREÇO DO YAML]. Quer marcar uma visita?"
  ✅ Otto deve fornecer endereço do YAML

Cenário 3: Agendamento (sem integração)
  Usuário: "Quero agendar uma reunião"
  Otto: "Ótimo! Pra agendar, você pode acessar [LINK_CALENDLY] e escolher o melhor horário. Ou se preferir, me passa seu email que peço pra equipe entrar em contato."
  ✅ Otto NÃO deve dizer que agendou
  ✅ Otto deve oferecer alternativas

Cenário 4: Continuidade na mesma sessão
  [Após 5 mensagens sobre sistemas sob medida]
  Usuário: "Quanto custa mais ou menos?"
  Otto: "Para sistemas sob medida como o que você precisa pro escritório, os projetos geralmente partem de R$ X.XXX..."
  ✅ Otto deve lembrar que é sobre escritório de advocacia

Cenário 5: Continuidade cross-sessão (NOVO)
  [Usuário conversou há 3 dias, sessão Redis expirou]
  Usuário: "Oi, tudo bem?"
  Otto: "Oi Maria! Faz um tempinho que não conversamos. Tudo bem sim! 
         Na última vez você estava interessada em sistemas para escritório de advocacia.
         Quer continuar de onde paramos?"
  ✅ Otto deve recuperar nome e contexto do Firestore
  ✅ Otto deve reconhecer que é um lead recorrente
```

---

## Arquivos a Criar/Modificar

| Arquivo | Ação | Prioridade | Status |
|---------|------|------------|--------|
| `src/ai/config/institutional_context.yaml` | Criar | P0 | ✅ |
| `src/ai/config/institutional_loader.py` | Criar | P0 | ✅ |
| `src/ai/prompts/system_role.py` | Modificar | P0 | ✅ |
| `src/ai/prompts/response_agent_prompt.py` | Modificar | P0 | ✅ |
| `src/ai/prompts/state_agent_prompt.py` | Modificar | P1 | ✅ |
| `src/ai/prompts/decision_agent_prompt.py` | Modificar | P1 | ✅ |
| `src/ai/services/orchestrator.py` | Modificar | P0 | ✅ |
| `src/app/sessions/models.py` | Modificar | P1 | ✅ |
| `src/ai/services/lead_extractor.py` | Criar | P1 | ✅ |
| `src/app/protocols/conversation_store.py` | Criar | P1 | ✅ |
| `src/app/infra/stores/firestore_conversation_store.py` | Criar | P1 | ✅ |
| `src/app/sessions/manager.py` | Modificar | P1 | ✅ |
| `src/app/bootstrap/whatsapp_factory.py` | Modificar | P1 | ✅ |
| `tests/test_ai/test_institutional_loader.py` | Criar | P1 | ✅ |
| `tests/test_ai/test_lead_extractor.py` | Criar | P1 | ✅ |
| `tests/app/protocols/test_conversation_store.py` | Criar | P1 | ✅ |
| `tests/app/sessions/test_session_manager.py` | Criar | P1 | ✅ |

---

## Histórico de Alterações

| Data | Autor | Alteração |
|------|-------|-----------|
| 03/02/2026 | Auditoria | Documento criado com base em análise do código |
| 03/02/2026 | Auditoria | Adicionadas tarefas P1.7-P1.11 para persistência de conversas |
| 03/02/2026 | Auditoria | Adicionada seção 7 (Especificação Firestore) |
| 04/02/2026 | Executor | ✅ Concluído P0.1-P0.5 (tarefas críticas) |
| 04/02/2026 | Executor | ✅ Concluído P1.1-P1.8 (estruturas, persistência, prompts) |
| 04/02/2026 | Executor | Nova arquitetura de agentes (Phase1: State+Response paralelo → Phase2: MessageType → Phase3: Decision) |
| 04/02/2026 | Executor | Modelos por agente: GPT-5.1 (State/Decision), GPT-5.1-chat (Response), GPT-5-nano (MessageType) |
| 04/02/2026 | Executor | Threshold de confiança alterado para 0.7 |
| 04/02/2026 | Executor | ✅ Concluído P1.9-P1.11 (dual-write, recovery, testes) |
| 04/02/2026 | Executor | SessionManager com suporte a ConversationStore opcional |
| 04/02/2026 | Executor | 469 testes passando, cobertura mantida |

---

> **P0 e P1 CONCLUÍDOS!**
>
> **Próximos passos (P2):**
> 1. Integração Google Calendar
> 2. Ferramentas para o LLM agendar/verificar agenda
> 3. Integração WhatsApp Flows
> 3. Preencher campos `# TODO` no `institutional_context.yaml` com dados reais da Pyloto
