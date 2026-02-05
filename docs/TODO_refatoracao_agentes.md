# TODO: Refatoração para Arquitetura de Agente Único + Utilitários

**Data:** 05 de fevereiro de 2026  
**Objetivo:** Substituir pipeline de 4 agentes LLM por arquitetura Otto (agente único) + agentes utilitários paralelos  
**Status (05/fev/2026):** Concluído. Pipeline legado removido; documento mantido como referência histórica.
**Referência:** REGRAS_E_PADROES.md (raiz do repositório)  
**Estimativa:** 1-2 dias de desenvolvimento

---

## Contexto da Refatoração

### Arquitetura Atual (a remover)
```

Pipeline sequencial de 4 agentes LLM:
StateAgent → ResponseAgent → MessageTypeAgent → DecisionAgent
├─ Custo: ~\$0.0009/msg (4 chamadas LLM)
├─ Latência: ~3-4s
└─ Problema: Over-engineering para estágio atual

```

### Arquitetura Alvo
```

ExtractionAgent (paralelo) → Preenche LeadContact
TranscriptionAgent (se áudio) → Converte para texto
↓
OttoAgent (único)
├─ Context injection dinâmico por vertente
├─ Structured outputs (Pydantic)
└─ Decide estado + gera resposta + escolhe tipo msg
↓
ValidationPipeline (híbrido)
├─ Gate 1: Determinístico (sempre)
├─ Gate 2: Confidence check
└─ Gate 3: LLM review (se 0.7 < conf < 0.85)

```

**Ganhos esperados:**
- Custo: -66% (~$0.0003/msg)
- Latência: -25% (~2-2.5s)
- Qualidade: +40% (extração estruturada)
- Manutenibilidade: +100% (código mais simples)

---

## FASE 1: REMOÇÃO

### 1.1 Remover Pipeline de 4 Agentes ❌

**Arquivos a deletar:**
```bash
src/ai/models/state_agent.py
src/ai/models/message_type_selection.py
src/ai/prompts/state_agent_prompt.py
src/ai/prompts/message_type_agent_prompt.py
src/ai/prompts/decision_agent_prompt.py
src/ai/services/_orchestrator_helpers.py  # Helpers do pipeline antigo
src/ai/utils/agent_parser.py  # Parsers dos 4 agentes
```

**Arquivos a refatorar (não deletar):**

```bash
src/ai/models/response_generation.py  # Aproveitar estruturas
src/ai/models/decision_agent.py       # Aproveitar lógica de decisão
src/ai/services/orchestrator.py       # Reescrever como OttoAgent
```

**Checklist:**

- [ ] Backup dos arquivos atuais (criar branch `backup/4-agents-pipeline`)
- [ ] Deletar arquivos listados
- [ ] Remover imports dos arquivos deletados em:
- [ ] `src/ai/__init__.py`
- [ ] `src/app/use_cases/whatsapp/process_inbound_canonical.py`
- [ ] Executar `ruff check src/` (sem erros de import)
- [ ] Commit: `refactor: remove 4-agent pipeline`

---

### 1.2 Remover Testes dos Agentes Antigos ❌

**Arquivos a deletar:**

```bash
tests/test_ai/test_models_state_agent.py
tests/test_ai/test_models_decision_agent.py
tests/test_ai/test_utils_agent_parser.py
tests/test_ai/test_agent_prompts.py
tests/test_ai/test_ai_pipeline.py  # Pipeline antigo
```

**Checklist:**

- [ ] Deletar testes listados
- [ ] Executar `pytest tests/` (ignorar falhas esperadas)
- [ ] Commit: `test: remove 4-agent pipeline tests`

---

## FASE 2: AGENTES UTILITÁRIOS (Dias 3-4)

### 2.1 ExtractionAgent ✅ **PRIORITÁRIO**

**Objetivo:** Extrair informações estruturadas para preencher `LeadContact`

**Arquivo:** `src/ai/services/extraction_agent.py`

**Implementação:**

```python
"""
Agente especializado em extrair informações estruturadas.

Responsabilidades:
- Extrair dados pessoais (nome, email, telefone, empresa)
- Identificar serviços de interesse (SaaS, Sob Medida, etc)
- Detectar urgência e necessidade específica
- Estimar score de confiança da extração

Conformidade REGRAS_E_PADROES.md:
- § 1.2 SRP: Única responsabilidade (extraction)
- § 4: Arquivo ≤ 200 linhas
- § 5: PT-BR, snake_case, type hints
- § 6: Logs estruturados sem PII
"""

from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from typing import Literal
import re
from config.logging import get_logger

logger = get_logger(__name__)

class ExtractedLeadInfo(BaseModel):
    """Schema de output do ExtractionAgent (structured output)."""
    
    name: str | None = Field(None, description="Nome completo se mencionado")
    email: str | None = Field(None, description="Email válido")
    phone: str | None = Field(None, description="Telefone BR (com DDD)")
    company: str | None = Field(None, description="Nome da empresa")
    role: str | None = Field(None, description="Cargo/função")
    
    service_interest: list[Literal[
        "saas", "sob_medida", "gestao_perfis", 
        "trafego_pago", "automacao_atendimento", "intermediacao"
    ]] = Field(default_factory=list, description="Serviços mencionados")
    
    urgency: Literal["low", "medium", "high", "urgent"] | None = None
    budget_indication: str | None = Field(None, max_length=100)
    specific_need: str | None = Field(None, max_length=150)
    
    extraction_confidence: float = Field(ge=0.0, le=1.0)

class ExtractionAgent:
    """Agente utilitário para extração de informações."""
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
        self.model = "gpt-4o-mini"  # Barato e rápido
    
    async def extract(
        self,
        user_message: str,
        conversation_context: list[str] | None = None
    ) -> ExtractedLeadInfo:
        """
        Extrai informações estruturadas da mensagem.
        
        Executa EM PARALELO com OttoAgent (não aumenta latência).
        """
        # Implementar conforme spec
        pass
```

**Checklist:**

- [ ] Criar `src/ai/services/extraction_agent.py`
- [ ] Implementar `ExtractedLeadInfo` (Pydantic BaseModel)
- [ ] Implementar `ExtractionAgent.extract()` com structured outputs
- [ ] Adicionar validações:
- [ ] Email: regex RFC 5322
- [ ] Telefone: formato brasileiro (11) 9XXXX-XXXX
- [ ] Service interest: apenas valores válidos
- [ ] Adicionar logging estruturado (sem PII):

```python
logger.info("extraction_completed", extra={
    "fields_extracted": len([v for v in result.model_dump().values() if v]),
    "confidence": result.extraction_confidence,
    "tokens": response.usage.total_tokens,
    "cost_usd": response.usage.total_tokens * 0.00000015
})
```

- [ ] Testar isoladamente (criar `tests/test_ai/test_extraction_agent.py`)
- [ ] Garantir arquivo ≤ 200 linhas (§ 4)
- [ ] Executar `ruff check src/ai/services/extraction_agent.py`
- [ ] Commit: `feat(ai): add ExtractionAgent with structured outputs`

---

### 2.2 TranscriptionAgent ✅ **CRÍTICO PARA WHATSAPP**

**Objetivo:** Transcrever áudios do WhatsApp para texto

**Arquivo:** `src/ai/services/transcription_agent.py`

**Implementação:**

```python
"""
Agente especializado em transcrição de áudios.

Responsabilidades:
- Transcrever áudio WhatsApp (formato OGG/Opus)
- Usar Whisper API (OpenAI)
- Detectar idioma automaticamente
- Estimar confiança da transcrição

Conformidade REGRAS_E_PADROES.md:
- § 4: Arquivo ≤ 200 linhas
- § 6: Logs sem conteúdo do áudio (apenas metadata)
"""

from dataclasses import dataclass
from openai import AsyncOpenAI
import httpx
from config.logging import get_logger

logger = get_logger(__name__)

@dataclass
class TranscriptionResult:
    """Resultado da transcrição."""
    text: str
    language: str
    duration_seconds: float
    confidence: float  # Estimado
    error: str | None = None

class TranscriptionAgent:
    """Agente utilitário para transcrição de áudios."""
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
    
    async def transcribe(
        self,
        audio_file_url: str,
        language: str = "pt"
    ) -> TranscriptionResult:
        """
        Transcreve áudio do WhatsApp.
        
        SEMPRE executa antes do pipeline se message_type == "audio".
        """
        # Implementar conforme spec
        pass
    
    async def _download_audio(self, url: str) -> bytes:
        """Download do áudio via WhatsApp Media API."""
        # Implementar com httpx + auth token
        pass
    
    def _estimate_confidence(self, whisper_response) -> float:
        """Estima confiança baseado em palavras reconhecidas."""
        # Heurística: % palavras com >3 letras
        pass
```

**Checklist:**

- [ ] Criar `src/ai/services/transcription_agent.py`
- [ ] Implementar `TranscriptionAgent.transcribe()`
- [ ] Integrar Whisper API (modelo `whisper-1`)
- [ ] Implementar download de áudio:
    - [ ] Usar `httpx.AsyncClient`
    - [ ] Auth com WhatsApp token (ler de `settings.whatsapp.media_token`)
    - [ ] Timeout 30s
- [ ] Adicionar fallback se transcrição falha:

```python
return TranscriptionResult(
    text="[Áudio não pôde ser transcrito]",
    language=language,
    duration_seconds=0,
    confidence=0.0,
    error=str(e)
)
```

- [ ] Logging estruturado:

```python
logger.info("audio_transcribed", extra={
    "duration_seconds": result.duration_seconds,
    "text_length": len(result.text),
    "confidence": result.confidence,
    "cost_usd": result.duration_seconds * 0.006 / 60
})
```

- [ ] Testar com áudio real (mock opcional para CI)
- [ ] Arquivo ≤ 200 linhas
- [ ] Commit: `feat(ai): add TranscriptionAgent with Whisper API`

---

### 2.3 ContextInjector 🎯 **CORE DA REFATORAÇÃO**

**Objetivo:** Injetar contexto dinâmico por vertente Pyloto

**Arquivos:**

1. `src/ai/contexts/pyloto_verticals.py` (contextos das vertentes)
2. `src/ai/services/context_injector.py` (lógica de injeção)

**Implementação:**

**Arquivo 1:** `src/ai/contexts/pyloto_verticals.py`

```python
"""
Contextos detalhados das vertentes Pyloto.

Cada vertente tem:
- Descrição
- Público-alvo
- Pricing (ranges, não valores exatos)
- Features principais
- Use cases
- Cases de sucesso
- Objeções comuns + respostas
- Próximos passos
- FAQ

Conformidade REGRAS_E_PADROES.md:
- § 1.1: Clareza > esperteza (texto direto, sem jargão)
- § 4: Dividir em múltiplos arquivos se > 200 linhas cada contexto
"""

from dataclasses import dataclass
from typing import Literal

VerticalType = Literal[
    "saas", "sob_medida", "gestao_perfis",
    "trafego_pago", "automacao_atendimento", "intermediacao"
]

@dataclass
class VerticalContext:
    vertical: VerticalType
    description: str
    target_audience: str
    pricing: str
    features: list[str]
    use_cases: list[str]
    success_stories: list[str]
    common_objections: dict[str, str]
    next_steps: list[str]
    faq: dict[str, str]
    
    def to_prompt_context(self) -> str:
        """Converte para texto formatado (injeção no prompt)."""
        # Implementar formatação estruturada
        pass

# Instâncias dos contextos
SAAS_CONTEXT = VerticalContext(...)
SOB_MEDIDA_CONTEXT = VerticalContext(...)
GESTAO_PERFIS_CONTEXT = VerticalContext(...)
TRAFEGO_PAGO_CONTEXT = VerticalContext(...)
AUTOMACAO_ATENDIMENTO_CONTEXT = VerticalContext(...)
INTERMEDIACAO_CONTEXT = VerticalContext(...)
```

**Arquivo 2:** `src/ai/services/context_injector.py`

```python
"""
Injeta contexto dinâmico baseado em LeadContact.primary_interest.

Responsabilidades:
- Ler LeadContact.primary_interest
- Carregar contexto vertical relevante
- Combinar CORE + VERTICAL
- Ajustar por conversation_stage (discovery, objection, closing)

Conformidade REGRAS_E_PADROES.md:
- § 1.2 SRP: Única responsabilidade (context injection)
- § 3: Não importa de api/ (apenas app/protocols)
"""

from ai.contexts.pyloto_verticals import (
    SAAS_CONTEXT, SOB_MEDIDA_CONTEXT, # ... importar todos
)
from app.protocols.models import LeadContact
from typing import Literal
from config.logging import get_logger

logger = get_logger(__name__)

class ContextInjector:
    """Injeta contexto dinâmico por vertente."""
    
    CORE_CONTEXT = """
    Você é Otto, assistente virtual da Pyloto no WhatsApp.
    
    ## Sobre a Pyloto
    [Preencher com dados reais: endereço, horário, contato]
    
    ## Vertentes de Serviço
    [Lista resumida das 6 vertentes]
    """
    
    def __init__(self):
        self.vertical_contexts = {
            "saas": SAAS_CONTEXT,
            # ... mapear todos
        }
    
    def inject(
        self,
        lead_contact: LeadContact,
        conversation_stage: Literal["discovery", "qualification", "objection", "closing"]
    ) -> str:
        """Injeta contexto baseado em LeadContact.primary_interest."""
        # Implementar lógica conforme spec
        pass
```

**Checklist:**

- [ ] Criar `src/ai/contexts/` (novo diretório)
- [ ] Criar `src/ai/contexts/__init__.py` (exports)
- [ ] Criar `src/ai/contexts/pyloto_verticals.py`
- [ ] Preencher `CORE_CONTEXT` com dados reais Pyloto:
    - [ ] Endereço físico
    - [ ] Horário de funcionamento
    - [ ] Telefone/WhatsApp de contato
    - [ ] Email
- [ ] Implementar 6 contextos verticais:
    - [ ] `SAAS_CONTEXT` (clínicas, academias, salões)
    - [ ] `SOB_MEDIDA_CONTEXT` (desenvolvimento custom)
    - [ ] `GESTAO_PERFIS_CONTEXT` (redes sociais)
    - [ ] `TRAFEGO_PAGO_CONTEXT` (Google/Meta Ads)
    - [ ] `AUTOMACAO_ATENDIMENTO_CONTEXT` (chatbots IA)
    - [ ] `INTERMEDIACAO_CONTEXT` (marketplace serviços)
- [ ] Cada contexto deve ter:
    - [ ] Descrição (2-3 parágrafos)
    - [ ] Pricing (ranges, ex: "a partir de R\$ 159/mês")
    - [ ] 5-8 features principais
    - [ ] 3-5 use cases
    - [ ] 2-3 cases de sucesso (anonimizados se necessário)
    - [ ] 5+ objeções comuns + respostas
    - [ ] 4 próximos passos sugeridos
    - [ ] Top 5 FAQ
- [ ] Garantir cada contexto ≤ 800 tokens quando convertido
- [ ] Criar `src/ai/services/context_injector.py`
- [ ] Implementar `ContextInjector.inject()`
- [ ] Adicionar logging:

```python
logger.debug("context_injected", extra={
    "vertical": lead_contact.primary_interest,
    "conversation_stage": conversation_stage,
    "tokens_estimate": len(context.split()) * 1.3
})
```

- [ ] Testar cada contexto individualmente
- [ ] Verificar se arquivos ≤ 200 linhas (dividir se necessário)
- [ ] Commit: `feat(ai): add context injection system with vertical contexts`

---

## FASE 3: OTTOAGENT (Dias 5-6)

### 3.1 Reescrever Orchestrator como OttoAgent ✅

**Objetivo:** Agente único que decide estado + gera resposta + escolhe tipo mensagem

**Arquivo:** `src/ai/services/otto_agent.py` (renomear de `orchestrator.py`)

**Implementação:**

```python
"""
OttoAgent - Agente único de decisão e resposta.

Responsabilidades:
- Receber LeadContact já preenchido (por ExtractionAgent)
- Receber contexto dinâmico (por ContextInjector)
- Decidir próximo estado FSM
- Gerar resposta natural
- Escolher tipo de mensagem (text/button/list)
- Retornar decisão estruturada (OttoDecision)

Conformidade REGRAS_E_PADROES.md:
- § 1.2 SRP: Decisão + Resposta (acopladas por natureza)
- § 4: Arquivo ≤ 200 linhas
- § 5: Type hints completos
- § 6: Logs estruturados
- § 7: Structured outputs (não free-text parsing)
"""

from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from typing import Literal
from app.protocols.models import LeadContact, Session
from fsm.states.session import SessionState
from fsm.transitions.rules import VALID_TRANSITIONS
from ai.services.context_injector import ContextInjector
from config.logging import get_logger

logger = get_logger(__name__)

class OttoDecision(BaseModel):
    """Output estruturado do OttoAgent (structured output garantido)."""
    
    next_state: Literal[
        "INITIAL", "TRIAGE", "COLLECTING_INFO",
        "GENERATING_RESPONSE", "HANDOFF_HUMAN",
        "SELF_SERVE_INFO", "SCHEDULED_FOLLOWUP",
        "ROUTE_EXTERNAL", "TIMEOUT", "ERROR"
    ]
    
    response_text: str = Field(max_length=500)
    
    message_type: Literal["text", "interactive_button", "interactive_list"]
    
    confidence: float = Field(ge=0.0, le=1.0)
    
    reasoning: str = Field(
        description="Justificativa da decisão (debug/logs)"
    )
    
    requires_human: bool = False

class OttoAgent:
    """Agente único Otto."""
    
    def __init__(
        self,
        openai_client: AsyncOpenAI,
        context_injector: ContextInjector
    ):
        self.client = openai_client
        self.injector = context_injector
        self.model = "gpt-4o-2024-08-06"  # Structured outputs support
    
    async def process_message(
        self,
        user_input: str,
        session: Session,
        current_state: SessionState
    ) -> OttoDecision:
        """Processa mensagem e retorna decisão estruturada."""
        
        lead = session.lead_contact
        
        # 1. Detecta conversation_stage
        stage = self._detect_conversation_stage(session, user_input, lead)
        
        # 2. Injeta contexto dinâmico
        dynamic_context = self.injector.inject(
            lead_contact=lead,
            conversation_stage=stage
        )
        
        # 3. Monta prompt
        system_prompt = self._build_prompt(
            dynamic_context, lead, session, current_state
        )
        
        # 4. Chama LLM com structured output
        response = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            response_format=OttoDecision,
            temperature=0.7,
            max_tokens=800
        )
        
        decision: OttoDecision = response.choices.message.parsed
        
        # 5. Valida FSM transition
        if not self._is_valid_transition(current_state, decision.next_state):
            logger.warning("invalid_fsm_transition", extra={
                "from": current_state.value,
                "to": decision.next_state
            })
            decision.next_state = current_state.value
            decision.requires_human = True
        
        # 6. Log
        logger.info("otto_decision", extra={
            "next_state": decision.next_state,
            "confidence": decision.confidence,
            "lead_score": lead.qualification_score,
            "conversation_stage": stage,
            "tokens": response.usage.total_tokens,
            "cost_usd": response.usage.total_tokens * 0.0000025
        })
        
        return decision
    
    def _detect_conversation_stage(
        self, session: Session, user_input: str, lead: LeadContact
    ) -> Literal["discovery", "qualification", "objection", "closing"]:
        """Detecta estágio baseado em LeadContact e input."""
        # Implementar lógica conforme spec
        pass
    
    def _build_prompt(
        self, context: str, lead: LeadContact, 
        session: Session, state: SessionState
    ) -> str:
        """Monta prompt completo."""
        # Implementar conforme spec
        pass
    
    def _is_valid_transition(
        self, current: SessionState, next_state: str
    ) -> bool:
        """Valida se transição FSM é permitida."""
        try:
            next_enum = SessionState[next_state]
            return next_enum in VALID_TRANSITIONS.get(current, set())
        except KeyError:
            return False
```

**Checklist:**

- [ ] Renomear `src/ai/services/orchestrator.py` → `otto_agent.py`
- [ ] Deletar `_orchestrator_helpers.py` (não mais necessário)
- [ ] Criar `OttoDecision` (Pydantic BaseModel)
- [ ] Implementar `OttoAgent.__init__()`
- [ ] Implementar `OttoAgent.process_message()`
- [ ] Implementar `_detect_conversation_stage()`:
    - [ ] Discovery: score < 30
    - [ ] Qualification: score 30-59
    - [ ] Objection: keywords de objeção
    - [ ] Closing: score >= 60 + sinais de interesse
- [ ] Implementar `_build_prompt()`:
    - [ ] Combinar: context + LeadContact summary + history + FSM state
    - [ ] Max 2.500 tokens total
- [ ] Implementar `_is_valid_transition()` (usa VALID_TRANSITIONS do FSM)
- [ ] Adicionar fallback se LLM falha:

```python
except Exception as e:
    logger.error("otto_failed", exc_info=e)
    return OttoDecision(
        next_state=SessionState.HANDOFF_HUMAN.value,
        response_text="Desculpe, tive um problema. Conectando com a equipe...",
        message_type="text",
        confidence=0.0,
        reasoning=f"LLM failure: {e}",
        requires_human=True
    )
```

- [ ] Garantir arquivo ≤ 200 linhas (extrair helpers se necessário)
- [ ] Atualizar `src/ai/__init__.py` (exportar `OttoAgent`, remover antigos)
- [ ] Executar `ruff check src/ai/services/otto_agent.py`
- [ ] Commit: `refactor(ai): rewrite orchestrator as OttoAgent (single agent)`

---

### 3.2 ValidationPipeline (Híbrido) ✅

**Objetivo:** Validação em 3 gates (determinístico + confidence + LLM seletivo)

**Arquivo:** `src/ai/services/decision_validator.py`

**Implementação:**

```python
"""
Pipeline de validação híbrido para decisões do OttoAgent.

Gates:
1. Determinístico (sempre): FSM válida, PII, promessas proibidas
2. Confidence check: >= 0.85 aprova, < 0.7 escala, 0.7-0.85 → Gate 3
3. LLM review (seletivo): Valida apenas zona cinza

Conformidade REGRAS_E_PADROES.md:
- § 1.3: Determinismo (Gate 1 é 100% determinístico)
- § 4: Arquivo ≤ 200 linhas
- § 7: Defesa em profundidade (múltiplas camadas)
"""

from enum import Enum
from dataclasses import dataclass
from openai import AsyncOpenAI
from ai.services.otto_agent import OttoDecision
from app.protocols.models import Session
from fsm.states.session import SessionState
from fsm.transitions.rules import VALID_TRANSITIONS
from config.logging import get_logger
import re

logger = get_logger(__name__)

class ValidationType(Enum):
    DETERMINISTIC = "deterministic"
    LLM_LIGHTWEIGHT = "llm_lightweight"
    HUMAN_REQUIRED = "human"

@dataclass
class ValidationResult:
    approved: bool
    validation_type: ValidationType
    corrections: dict[str, any] | None = None
    reasoning: str = ""
    cost_usd: float = 0.0

class DecisionValidator:
    """Pipeline de validação híbrido."""
    
    HIGH_CONFIDENCE_THRESHOLD = 0.85
    LOW_CONFIDENCE_THRESHOLD = 0.70
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
    
    async def validate(
        self,
        decision: OttoDecision,
        session: Session,
        current_state: SessionState
    ) -> ValidationResult:
        """3-gate validation system."""
        
        # GATE 1: Determinístico (sempre)
        gate1 = self._validate_deterministic(decision, session, current_state)
        if not gate1.approved:
            return gate1
        
        # GATE 2: Confidence check
        if decision.confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            return ValidationResult(
                approved=True,
                validation_type=ValidationType.DETERMINISTIC,
                reasoning=f"High confidence ({decision.confidence:.2f})"
            )
        
        if decision.confidence < self.LOW_CONFIDENCE_THRESHOLD:
            return ValidationResult(
                approved=False,
                validation_type=ValidationType.HUMAN_REQUIRED,
                reasoning=f"Low confidence ({decision.confidence:.2f})"
            )
        
        # GATE 3: LLM review (apenas 0.7-0.85)
        return await self._validate_llm_lightweight(decision, session)
    
    def _validate_deterministic(
        self, decision: OttoDecision, session: Session, 
        current_state: SessionState
    ) -> ValidationResult:
        """Gate 1: Validações determinísticas."""
        # Implementar checks conforme spec
        pass
    
    async def _validate_llm_lightweight(
        self, decision: OttoDecision, session: Session
    ) -> ValidationResult:
        """Gate 3: Validação leve com gpt-4o-mini."""
        # Implementar conforme spec
        pass
```

**Checklist:**

- [ ] Criar `src/ai/services/decision_validator.py`
- [ ] Implementar `ValidationResult` (dataclass)
- [ ] Implementar `DecisionValidator.validate()`
- [ ] Implementar `_validate_deterministic()`:
    - [ ] Check FSM transition válida
    - [ ] Check response length < 1000 chars
    - [ ] Check PII sensível (CPF, cartão): regex
    - [ ] Check promessas proibidas: ["agendei", "confirmei", "enviei"]
    - [ ] Check coerência message_type (button precisa ter opções no texto)
- [ ] Implementar `_validate_llm_lightweight()`:
    - [ ] Usar `gpt-4o-mini` (barato)
    - [ ] Prompt de validação (1 linha: APPROVED/REJECTED)
    - [ ] Timeout 10s
- [ ] Adicionar thresholds configuráveis:

```python
# Em src/config/settings/ai/validation.py
HIGH_CONFIDENCE_THRESHOLD = 0.85
LOW_CONFIDENCE_THRESHOLD = 0.70
```

- [ ] Logging por gate:

```python
logger.info("gate1_deterministic", extra={"approved": result.approved})
logger.info("gate2_confidence", extra={"threshold_crossed": "high"})
logger.info("gate3_llm_review", extra={"cost_usd": result.cost_usd})
```

- [ ] Arquivo ≤ 200 linhas
- [ ] Commit: `feat(ai): add hybrid validation pipeline (3-gate)`

---

## FASE 4: ATUALIZAR LeadContact (Dia 7)

### 4.1 Expandir LeadContact Model ✅

**Objetivo:** LeadContact como single source of truth do lead

**Arquivo:** `src/app/protocols/models.py` (atualizar existente)

**Implementação:**

```python
# Adicionar ao arquivo existente

class LeadContact(BaseModel):
    """
    Perfil do lead, preenchido progressivamente pelo ExtractionAgent.
    
    Esta classe é sempre carregada no prompt do Otto.
    """
    
    # Identificação
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    location: str | None = None
    
    # Interesse (CRÍTICO para context injection)
    primary_interest: Literal[
        "saas", "sob_medida", "gestao_perfis",
        "trafego_pago", "automacao_atendimento", "intermediacao"
    ] | None = None
    
    secondary_interests: list[str] = Field(default_factory=list)
    
    # Qualificação
    urgency: Literal["low", "medium", "high", "urgent"] | None = None
    budget_indication: str | None = None
    specific_need: str | None = Field(None, max_length=150)
    company_size: Literal["mei", "micro", "pequena", "media", "grande"] | None = None
    
    # Scores
    qualification_score: float = Field(default=0.0, ge=0.0, le=100.0)
    is_qualified: bool = False
    
    # Metadados
    first_contact_at: datetime | None = None
    last_updated_at: datetime | None = None
    total_messages: int = 0
    
    # Flags
    requested_human: bool = False
    showed_objection: bool = False
    
    def to_prompt_summary(self) -> str:
        """Converte para texto resumido (max 200 tokens)."""
        # Implementar conforme spec
        pass
    
    def calculate_qualification_score(self) -> float:
        """
        Calcula score 0-100 baseado em campos preenchidos.
        
        Critérios:
        - Nome: +15
        - Contato: +15
        - Empresa: +10
        - Interesse: +20
        - Necessidade: +15
        - Urgência alta: +15
        - Budget: +10
        """
        # Implementar conforme spec
        pass
```

**Checklist:**

- [ ] Adicionar novos campos em `LeadContact`
- [ ] Implementar `to_prompt_summary()`:
    - [ ] Formato conciso (bullet points)
    - [ ] Max 200 tokens
    - [ ] Destacar campos críticos (interesse, urgência)
- [ ] Implementar `calculate_qualification_score()`:
    - [ ] Score 0-100
    - [ ] `is_qualified = score >= 60`
    - [ ] Atualizar `self.qualification_score` e `self.is_qualified`
- [ ] Adicionar validações Pydantic:
    - [ ] Email: `Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')`
    - [ ] Phone: `Field(..., pattern=r'^\(\d{2}\) 9?\d{4}-?\d{4}$')`
- [ ] Executar `ruff check src/app/protocols/models.py`
- [ ] Commit: `feat(app): expand LeadContact model with qualification scoring`

---

### 4.2 Merge Strategy (ExtractionAgent → LeadContact) ✅

**Objetivo:** Lógica de merge inteligente (não sobrescrever dados anteriores)

**Arquivo:** `src/app/use_cases/whatsapp/_inbound_helpers.py` (criar helper)

**Implementação:**

```python
"""
Helpers para merge de extracted info em LeadContact.

Conformidade REGRAS_E_PADROES.md:
- § 4: Arquivo ≤ 200 linhas
- § 5: Type hints completos
"""

from app.protocols.models import LeadContact
from ai.services.extraction_agent import ExtractedLeadInfo
from config.logging import get_logger

logger = get_logger(__name__)

def merge_extracted_info(
    lead: LeadContact,
    extracted: ExtractedLeadInfo
) -> LeadContact:
    """
    Merge extracted info em LeadContact.
    
    Estratégia:
    - Campos de identificação: não sobrescrever (primeira captura vale)
    - Interesse: atualizar se mais específico
    - Urgência: sempre atualizar (pode mudar)
    - Necessidade: append (não sobrescrever)
    """
    
    # Identificação (só preenche se vazio)
    if extracted.name and not lead.name:
        lead.name = extracted.name
        logger.info("lead_name_captured", extra={"name": extracted.name})
    
    # ... implementar resto
    
    # Recalcula score
    lead.calculate_qualification_score()
    
    return lead
```

**Checklist:**

- [ ] Criar `src/app/use_cases/whatsapp/_inbound_helpers.py`
- [ ] Implementar `merge_extracted_info()`:
    - [ ] Nome: primeira captura (não sobrescreve)
    - [ ] Email: primeira captura
    - [ ] Phone: primeira captura
    - [ ] Company: primeira captura
    - [ ] Interesse primário: primeira captura, novos viram secundários
    - [ ] Urgência: sempre atualiza (pode aumentar/diminuir)
    - [ ] Necessidade: append com ";" (max 150 chars)
    - [ ] Budget: atualiza se fornecido
- [ ] Logging estruturado para cada captura
- [ ] Chamar `lead.calculate_qualification_score()` ao final
- [ ] Arquivo ≤ 200 linhas
- [ ] Commit: `feat(app): add merge strategy for extracted lead info`

---

## FASE 5: INTEGRAÇÃO NO USE CASE (Dia 8)

### 5.1 Reescrever ProcessInboundCanonicalUseCase ✅

**Objetivo:** Integrar Otto + agentes utilitários + validação

**Arquivo:** `src/app/use_cases/whatsapp/process_inbound_canonical.py`

**Implementação:**

```python
"""
Use case canônico de processamento de mensagem inbound.

Pipeline:
1. Fast-path (70% dos casos, 0 LLMs)
2. Transcrição (se áudio)
3. Parallel: Otto + Extraction
4. Merge extracted → LeadContact
5. Validation (3-gate)
6. Update session
7. Return command

Conformidade REGRAS_E_PADROES.md:
- § 1.2 SRP: Orquestração do pipeline (não lógica de negócio)
- § 4: Arquivo ≤ 200 linhas
"""

import asyncio
from app.protocols.models import InboundEvent, OutboundCommand, Session
from ai.services.otto_agent import OttoAgent
from ai.services.extraction_agent import ExtractionAgent
from ai.services.transcription_agent import TranscriptionAgent
from ai.services.decision_validator import DecisionValidator
from app.use_cases.whatsapp._inbound_helpers import merge_extracted_info
from config.logging import get_logger

logger = get_logger(__name__)

class ProcessInboundCanonicalUseCase:
    """Use case de processamento de mensagem inbound."""
    
    def __init__(
        self,
        otto_agent: OttoAgent,
        extraction_agent: ExtractionAgent,
        transcription_agent: TranscriptionAgent,
        decision_validator: DecisionValidator,
        session_manager: SessionManager,
    ):
        self.otto = otto_agent
        self.extraction = extraction_agent
        self.transcription = transcription_agent
        self.validator = decision_validator
        self.sessions = session_manager
    
    async def execute(self, event: InboundEvent) -> OutboundCommand:
        """Pipeline completo."""
        
        # 1. Load session
        session = await self.sessions.resolve_or_create(event.sender_id)
        
        # 2. Transcrição (se áudio)
        if event.message_type == "audio":
            # Implementar conforme spec
            pass
        
        # 3. Fast-path
        fast_result = self._classify_fast_path(event.message_text)
        if fast_result:
            return OutboundCommand(text=fast_result.response, message_type="text")
        
        # 4. Parallel: Otto + Extraction
        decision, extracted = await asyncio.gather(
            self.otto.process_message(
                user_input=event.message_text,
                session=session,
                current_state=session.current_state
            ),
            self.extraction.extract(
                user_message=event.message_text,
                conversation_context=session.history[-3:]
            )
        )
        
        # 5. Merge extracted → LeadContact
        session.lead_contact = merge_extracted_info(
            lead=session.lead_contact,
            extracted=extracted
        )
        
        # 6. Validation (3-gate)
        validation = await self.validator.validate(
            decision=decision,
            session=session,
            current_state=session.current_state
        )
        
        if not validation.approved:
            # Implementar handling de rejeição
            pass
        
        # 7. Update session
        session.current_state = decision.next_state
        session.add_to_history(event.message_text, role="user")
        session.add_to_history(decision.response_text, role="assistant")
        await self.sessions.save(session)
        
        # 8. Return
        return OutboundCommand(
            text=decision.response_text,
            message_type=decision.message_type,
            next_state=decision.next_state
        )
```

**Checklist:**

- [ ] Reescrever `execute()` com novo pipeline
- [ ] Implementar fast-path (regex para saudações/FAQs):

```python
def _classify_fast_path(self, text: str) -> FastPathResult | None:
    if re.match(r"^(oi|olá|bom dia)", text.lower()):
        return FastPathResult(response="Oi! Como posso ajudar?")
    # ... mais regras
    return None
```

- [ ] Integrar TranscriptionAgent:

```python
if event.message_type == "audio":
    transcription = await self.transcription.transcribe(event.media_url)
    if transcription.confidence < 0.6:
        return OutboundCommand(text="Não consegui entender o áudio...")
    event.message_text = transcription.text
```

- [ ] Paralelizar Otto + Extraction:

```python
decision, extracted = await asyncio.gather(
    self.otto.process_message(...),
    self.extraction.extract(...)
)
```

- [ ] Merge extracted info
- [ ] Validar com ValidationPipeline
- [ ] Handling de validação rejeitada:
    - [ ] Se HUMAN_REQUIRED: escalar
    - [ ] Se corrections: aplicar e logar
- [ ] Notificar time se lead qualificar:

```python
if lead.is_qualified and not session.metadata.get("notified"):
    await self.notify_qualified_lead(lead, session)
    session.metadata["notified"] = True
```

- [ ] Logging estruturado de métricas:

```python
logger.info("pipeline_completed", extra={
    "lead_score": lead.qualification_score,
    "is_qualified": lead.is_qualified,
    "validation_type": validation.validation_type.value,
    "total_cost_usd": # calcular
})
```

- [ ] Arquivo ≤ 200 linhas (extrair helpers se necessário)
- [ ] Executar `ruff check src/app/use_cases/whatsapp/`
- [ ] Commit: `refactor(app): rewrite use case with Otto + utilities pipeline`

---

### 5.2 Atualizar Bootstrap (Wiring) ✅

**Objetivo:** Instanciar novos agentes e injetar dependências

**Arquivo:** `src/app/bootstrap/whatsapp_factory.py`

**Implementação:**

```python
"""
Factory de componentes WhatsApp.

Conformidade REGRAS_E_PADROES.md:
- § 3: Único lugar para wiring (bootstrap)
"""

from openai import AsyncOpenAI
from ai.services.otto_agent import OttoAgent
from ai.services.extraction_agent import ExtractionAgent
from ai.services.transcription_agent import TranscriptionAgent
from ai.services.context_injector import ContextInjector
from ai.services.decision_validator import DecisionValidator
from app.use_cases.whatsapp.process_inbound_canonical import (
    ProcessInboundCanonicalUseCase
)
from config.settings.ai.openai import OpenAISettings

def create_whatsapp_use_case() -> ProcessInboundCanonicalUseCase:
    """Cria use case com todas dependências."""
    
    # OpenAI client
    openai_settings = OpenAISettings()
    openai_client = AsyncOpenAI(api_key=openai_settings.api_key)
    
    # Agentes utilitários
    extraction_agent = ExtractionAgent(openai_client)
    transcription_agent = TranscriptionAgent(openai_client)
    context_injector = ContextInjector()
    
    # Otto (agente principal)
    otto_agent = OttoAgent(
        openai_client=openai_client,
        context_injector=context_injector
    )
    
    # Validator
    decision_validator = DecisionValidator(openai_client)
    
    # Session manager (existente)
    session_manager = create_session_manager()
    
    # Use case
    return ProcessInboundCanonicalUseCase(
        otto_agent=otto_agent,
        extraction_agent=extraction_agent,
        transcription_agent=transcription_agent,
        decision_validator=decision_validator,
        session_manager=session_manager
    )
```

**Checklist:**

- [ ] Atualizar `src/app/bootstrap/whatsapp_factory.py`
- [ ] Remover instanciações de agentes antigos:
    - [ ] StateAgent
    - [ ] ResponseAgent
    - [ ] MessageTypeAgent
    - [ ] DecisionAgent
    - [ ] AIOrchestrator (antigo)
- [ ] Adicionar instanciações de novos componentes:
    - [ ] ExtractionAgent
    - [ ] TranscriptionAgent
    - [ ] ContextInjector
    - [ ] OttoAgent
    - [ ] DecisionValidator
- [ ] Atualizar `create_whatsapp_use_case()`
- [ ] Executar `ruff check src/app/bootstrap/`
- [ ] Commit: `refactor(app): update bootstrap with new Otto architecture`

---

## FASE 6: TESTES (Dias 9-10)

### 6.1 Testes Unitários dos Agentes Utilitários ✅

**Arquivos de teste:**

1. `tests/test_ai/test_extraction_agent.py`
2. `tests/test_ai/test_transcription_agent.py`
3. `tests/test_ai/test_context_injector.py`
4. `tests/test_ai/test_otto_agent.py`
5. `tests/test_ai/test_decision_validator.py`

**Checklist:**

- [ ] Criar `tests/test_ai/test_extraction_agent.py`:
    - [ ] Test: extrai nome corretamente
    - [ ] Test: extrai email válido
    - [ ] Test: detecta service_interest (saas, sob_medida, etc)
    - [ ] Test: detecta urgência (keywords: urgente, hoje, etc)
    - [ ] Test: retorna confidence score
    - [ ] Test: fallback se LLM falha
- [ ] Criar `tests/test_ai/test_transcription_agent.py`:
    - [ ] Test: transcreve áudio mock (usar fixture)
    - [ ] Test: detecta idioma pt-BR
    - [ ] Test: fallback se download falha
    - [ ] Test: confidence estimation
- [ ] Criar `tests/test_ai/test_context_injector.py`:
    - [ ] Test: injeta SAAS_CONTEXT se primary_interest="saas"
    - [ ] Test: injeta SOB_MEDIDA_CONTEXT se primary_interest="sob_medida"
    - [ ] Test: injeta apenas CORE_CONTEXT se primary_interest=None
    - [ ] Test: modo discovery se lead não qualificado
    - [ ] Test: modo objection se conversation_stage="objection"
- [ ] Criar `tests/test_ai/test_otto_agent.py`:
    - [ ] Test: retorna OttoDecision válido
    - [ ] Test: detecta conversation_stage="discovery" se score < 30
    - [ ] Test: detecta conversation_stage="closing" se qualificado + interesse
    - [ ] Test: valida FSM transition antes de retornar
    - [ ] Test: fallback se LLM falha
- [ ] Criar `tests/test_ai/test_decision_validator.py`:
    - [ ] Test: Gate 1 rejeita FSM inválida
    - [ ] Test: Gate 1 rejeita PII sensível (CPF)
    - [ ] Test: Gate 1 rejeita promessas proibidas
    - [ ] Test: Gate 2 aprova se confidence >= 0.85
    - [ ] Test: Gate 2 escala se confidence < 0.7
    - [ ] Test: Gate 3 chama LLM se 0.7 <= confidence < 0.85
- [ ] Executar `pytest tests/test_ai/ -v`
- [ ] Garantir cobertura >= 80% nos novos arquivos:

```bash
pytest tests/test_ai/ --cov=src/ai/services --cov-report=term
```

- [ ] Commit: `test(ai): add comprehensive tests for Otto architecture`

---

### 6.2 Testes de Integração (Use Case) ✅

**Arquivo:** `tests/app/use_cases/whatsapp/test_process_inbound_canonical_v2.py`

**Cenários de teste:**

1. **Fast-path**: Saudação simples → resposta determinística
2. **Áudio**: Transcrição → Otto processa
3. **Primeira interação**: Sem dados → Otto coleta nome
4. **Qualificação progressiva**: Nome → empresa → interesse → qualificado
5. **Objeção**: Lead levanta objeção de preço → Otto consulta contexto
6. **Escalação**: Confiança baixa → escala para humano
7. **Validação**: Decisão inválida → correção automática

**Checklist:**

- [ ] Criar `tests/app/use_cases/whatsapp/test_process_inbound_canonical_v2.py`
- [ ] Implementar fixtures:
    - [ ] Mock OpenAI client (respostas canned)
    - [ ] Mock SessionManager (in-memory)
    - [ ] Mock WhatsApp Media API (para transcription)
- [ ] Implementar 7 cenários de teste
- [ ] Testar métricas são logadas corretamente
- [ ] Testar LeadContact.qualification_score atualiza
- [ ] Testar notificação de lead qualificado
- [ ] Executar `pytest tests/app/use_cases/ -v`
- [ ] Garantir cobertura >= 70% no use case
- [ ] Commit: `test(app): add integration tests for Otto pipeline`

---

### 6.3 Testes E2E (Opcional, mas recomendado) ✅

**Objetivo:** Testar fluxo completo com API real (staging)

**Arquivo:** `tests/e2e/test_otto_conversation_flow.py`

**Cenários:**

1. Conversa completa: Oi → Nome → Empresa → Interesse SaaS → Qualificado
2. Conversa com áudio: Envio áudio → Transcrição → Resposta
3. Objeção tratada: Interesse → Objeção preço → Case de sucesso → Agendar demo

**Checklist (opcional):**

- [ ] Criar `tests/e2e/test_otto_conversation_flow.py`
- [ ] Usar WhatsApp Test Number (sandbox)
- [ ] Implementar 3 cenários E2E
- [ ] Executar apenas em staging: `pytest tests/e2e/ -v -m staging`
- [ ] Validar métricas no dashboard (custo, latência, qualificação)
- [ ] Commit: `test(e2e): add conversation flow tests`

---

## FASE 7: DOCUMENTAÇÃO E DEPLOY (Dia 10)

### 7.1 Atualizar Documentação ✅

**Arquivos a atualizar:**

1. `README.md` (overview da arquitetura)
2. `AUDITORIA_ARQUITETURA.md` (refletir nova estrutura)
3. `docs/OTTO_ARCHITECTURE.md` (novo, detalhamento técnico)

**Checklist:**

- [ ] Atualizar `README.md`:
    - [ ] Seção "Arquitetura" com diagrama Otto
    - [ ] Listar agentes utilitários
    - [ ] Atualizar métricas (custo, latência)
- [ ] Atualizar `AUDITORIA_ARQUITETURA.md`:
    - [ ] Marcar pipeline de 4 agentes como "REMOVIDO"
    - [ ] Adicionar seção "Otto Architecture"
    - [ ] Atualizar métricas de cobertura de testes
- [ ] Criar `docs/OTTO_ARCHITECTURE.md`:
    - [ ] Diagrama de fluxo completo
    - [ ] Especificação de cada agente
    - [ ] Context injection strategy
    - [ ] Validation pipeline (3-gate)
    - [ ] Exemplos de uso
- [ ] Atualizar `TODO_llm.md`:
    - [ ] Marcar itens concluídos
    - [ ] Adicionar novos itens (ex: fine-tuning, SentimentAgent)
- [ ] Commit: `docs: update architecture documentation for Otto`

---

### 7.2 Deploy em Staging ✅

**Objetivo:** Validar em ambiente real antes de produção

**Checklist:**

- [ ] Executar suite completa de testes localmente:

```bash
ruff check src/
pytest tests/ -v
pytest --cov=src --cov-report=term
```

- [ ] Verificar cobertura geral >= 55% (meta mínima atual)
- [ ] Build Docker image:

```bash
docker build -t atende-pyloto:otto-v1 .
```

- [ ] Deploy no Google Cloud Run (staging):

```bash
gcloud run deploy atende-pyloto-staging \
  --image gcr.io/pyloto/atende-pyloto:otto-v1 \
  --region us-central1
```

- [ ] Configurar env vars:
    - [ ] `OPENAI_API_KEY`
    - [ ] `WHATSAPP_VERIFY_TOKEN`
    - [ ] `FIRESTORE_PROJECT_ID`
    - [ ] `REDIS_URL`
- [ ] Testar webhook WhatsApp:
    - [ ] Enviar "oi" → receber resposta
    - [ ] Enviar áudio → verificar transcrição
    - [ ] Enviar "preciso de sistema para clínica" → verificar contexto SaaS injetado
- [ ] Monitorar logs (30min):

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=atende-pyloto-staging" --limit 50
```

- [ ] Validar métricas:
    - [ ] Custo médio/msg: ~\$0.0003 (vs \$0.0009 antigo)
    - [ ] Latência P95: < 3s
    - [ ] Taxa de qualificação: >= 20%
- [ ] Se tudo OK, commit: `deploy: Otto v1 to staging`

---

### 7.3 Rollout Produção (Cauteloso) ✅

**Objetivo:** Deploy gradual em produção

**Checklist:**

- [ ] Validar staging por 24-48h:
    - [ ] 0 erros críticos
    - [ ] Métricas dentro do esperado
    - [ ] Feedback de usuários teste positivo
- [ ] Criar feature flag (opcional):

```python
# Em settings
USE_OTTO_ARCHITECTURE = os.getenv("USE_OTTO", "false") == "true"
```

- [ ] Deploy produção com rollout gradual:
    - [ ] 10% tráfego → Otto
    - [ ] 90% tráfego → Pipeline antigo (fallback)
    - [ ] Monitorar 2h
    - [ ] Se OK: 50% tráfego
    - [ ] Monitorar 4h
    - [ ] Se OK: 100% tráfego
- [ ] Monitorar métricas produção (72h):
    - [ ] Taxa de erro
    - [ ] Latência
    - [ ] Custo LLM
    - [ ] Taxa de qualificação de leads
    - [ ] NPS/satisfação usuário
- [ ] Se métricas degradarem:
    - [ ] Rollback imediato para pipeline antigo
    - [ ] Investigar root cause
    - [ ] Corrigir em staging
    - [ ] Retry deploy
- [ ] Se métricas melhorarem:
    - [ ] Deletar código do pipeline antigo
    - [ ] Commit: `feat: Otto architecture fully deployed to production`
    - [ ] Atualizar versão: `v2.0.0`

---

## MÉTRICAS DE SUCESSO

**Antes (Pipeline 4 Agentes):**

- Custo/msg: ~\$0.0009
- Latência P95: ~3.5s
- Taxa qualificação: desconhecida
- Cobertura testes AI: 95%
- Manutenibilidade: média (complexo)

**Depois (Otto + Utilitários) - Meta:**

- Custo/msg: ~\$0.0003 (-66%)
- Latência P95: ~2.5s (-28%)
- Taxa qualificação: >= 20%
- Cobertura testes AI: >= 80%
- Manutenibilidade: alta (simples)

---

## ROLLBACK PLAN

Se algo der errado, execute:

```bash
# 1. Reverter para branch anterior
git checkout backup/4-agents-pipeline

# 2. Deploy staging/produção
gcloud run deploy atende-pyloto-staging --image [imagem anterior]

# 3. Investigar problema
# - Logs: gcloud logging read ...
# - Métricas: dashboard Firestore/BigQuery
# - Reproduzir localmente

# 4. Corrigir e retry
```


---

## ORDEM DE EXECUÇÃO RECOMENDADA

**Dia 1:** Fase 1 (Remoção)
**Dia 2:** Fase 1 (Remoção de testes)
**Dia 3:** Fase 2.1 (ExtractionAgent)
**Dia 4:** Fase 2.2 (TranscriptionAgent) + 2.3 (ContextInjector - início)
**Dia 5:** Fase 2.3 (ContextInjector - conclusão) + 3.1 (OttoAgent - início)
**Dia 6:** Fase 3.1 (OttoAgent - conclusão) + 3.2 (ValidationPipeline)
**Dia 7:** Fase 4 (LeadContact) + Fase 5.1 (Use Case)
**Dia 8:** Fase 5.2 (Bootstrap) + Fase 6.1 (Testes unitários)
**Dia 9:** Fase 6.2 (Testes integração) + Fase 6.3 (E2E opcional)
**Dia 10:** Fase 7 (Documentação + Deploy staging)
**Dia 11+:** Monitoramento + Deploy produção gradual

---

## NOTAS IMPORTANTES

1. **Seguir REGRAS_E_PADROES.md rigorosamente:**
    - § 4: Todos arquivos ≤ 200 linhas
    - § 5: PT-BR, snake_case, type hints
    - § 6: Logs estruturados sem PII
    - § 9: Gates (ruff + pytest) devem passar
2. **Structured Outputs (OpenAI):**
    - Usar `beta.chat.completions.parse()` com `response_format=PydanticModel`
    - Disponível apenas em: `gpt-4o-2024-08-06`, `gpt-4o-mini-2024-07-18`
    - Documentação: https://platform.openai.com/docs/guides/structured-outputs
3. **Context Injection:**
    - Preencher contextos com dados REAIS da Pyloto
    - Não usar placeholders em produção
    - Validar cada contexto ≤ 800 tokens
4. **Testes são críticos:**
    - Não pular Fase 6
    - Cobertura mínima: 80% nos novos arquivos
    - E2E opcional mas altamente recomendado
5. **Deploy gradual:**
    - Staging primeiro (obrigatório)
    - Produção com rollout 10% → 50% → 100%
    - Monitorar métricas continuamente

---

## CHECKLIST FINAL

Antes de considerar concluído:

- [ ] Todos arquivos ≤ 200 linhas
- [ ] `ruff check src/` passa sem erros
- [ ] `pytest tests/` passa 100%
- [ ] Cobertura >= 80% nos arquivos novos
- [ ] Documentação atualizada
- [ ] Deploy staging OK (24-48h)
- [ ] Métricas validadas (custo, latência, qualificação)
- [ ] Rollback plan testado
- [ ] Commit final: `feat: Otto architecture v2.0.0`

---

**Dúvidas ou bloqueios:** Abrir issue no GitHub ou consultar REGRAS_E_PADROES.md

**Boa refatoração! 🚀**

```
<span style="display:none">[^1]</span>

<div align="center">⁂</div>

[^1]: Captura-de-tela-em-2026-02-04-17-06-12.jpg```
