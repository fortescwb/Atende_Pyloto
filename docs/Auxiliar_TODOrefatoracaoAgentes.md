**Vou mapear exatamente o que vem no webhook do WhatsApp e o que você deve persistir no banco.**

## WhatsApp Cloud API Webhook Payload - Campos Disponíveis

### Payload Completo (Inbound Message)
```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "5544999998888",  // Número da Pyloto
          "phone_number_id": "123456789012345"      // ID do número business (Pyloto)
        },
        "contacts": [{                                // ← DADOS DO USUÁRIO
          "profile": {
            "name": "João Silva"                     // Nome salvo no WhatsApp do usuário (Nem sempre será o nome do usuário)
          },
          "wa_id": "5544988887777"                   // Número do usuário (único, sempre vem)
        }],
        "messages": [{
          "id": "wamid.HBgNNTU0NDk4ODg4Nzc3NxUCABIYFjNFQjBGMDhCMzREOEQ3RjIxRDY2",
          "from": "5544988887777",                   // Número do usuário (repetido)
          "timestamp": "1738765432",                 // Unix timestamp
          "type": "text",                            // text, audio, image, video, document
          "text": {
            "body": "Oi, preciso de um sistema para minha clínica"
          }
        }]
      },
      "field": "messages"
    }]
  }]
}
```

### Dados Disponíveis Automaticamente (sem precisar extrair)

| Campo Webhook | Sempre Disponível? | Descrição | Exemplo |
|---|---|---|---|
| `contacts[0].wa_id` | ✅ SIM | Número WhatsApp do usuário (ID único) | `"5544988887777"` |
| `contacts[0].profile.name` | ✅ SIM | Nome salvo no WhatsApp do usuário | `"João Silva"` |
| `messages[0].from` | ✅ SIM | Número do usuário (igual ao `wa_id`) | `"5544988887777"` |
| `messages[0].id` | ✅ SIM | ID da mensagem (único por mensagem) | `"wamid.HBgN..."` |
| `messages[0].timestamp` | ✅ SIM | Unix timestamp da mensagem | `"1738765432"` |
| `metadata.phone_number_id` | ✅ SIM | ID do número business da Pyloto | `"123456789012345"` |

**Conclusão:** Telefone e nome do usuário **sempre vêm** no webhook. Você não precisa extrair, apenas ler do payload.

***

## LeadContact - Schema Definitivo para Banco de Dados

```python
# src/app/protocols/models.py

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Literal
import re

class LeadContact(BaseModel):
    """
    Perfil do lead armazenado no banco de dados (Firestore).
    
    Campos preenchidos:
    1. Automaticamente do webhook WhatsApp (wa_id, phone, whatsapp_name)
    2. Progressivamente pelo ExtractionAgent (nome real, email, empresa, etc)
    
    Storage: Firestore collection `lead_contacts`
    Document ID: `wa_id` (WhatsApp ID único)
    """
    
    # ============================================================
    # IDENTIFICAÇÃO (do WhatsApp - SEMPRE disponível no webhook)
    # ============================================================
    
    wa_id: str = Field(
        ...,  # Required (vem do webhook)
        description="WhatsApp ID único do usuário (igual ao número do telefone). Ex: '5544988887777'",
        pattern=r"^\d{12,15}$"  # 12-15 dígitos (formato internacional)
    )
    
    phone: str = Field(
        ...,  # Required (vem do webhook, igual ao wa_id)
        description="Número de telefone com código do país. Ex: '5544988887777'",
        pattern=r"^\d{12,15}$"
    )
    
    whatsapp_name: str = Field(
        ...,  # Required (vem do webhook - contacts[0].profile.name)
        description="Nome salvo no WhatsApp do usuário. Ex: 'João Silva'"
    )
    
    # ============================================================
    # DADOS PESSOAIS (extraídos pelo ExtractionAgent)
    # ============================================================
    
    full_name: str | None = Field(
        None,
        description="Nome completo extraído da conversa (pode ser diferente do whatsapp_name). Ex: 'Dr. João Pedro Silva'"
    )
    
    email: str | None = Field(
        None,
        description="Email extraído da conversa. Ex: 'joao@clinica.com'",
        pattern=r"^[^@]+@[^@]+\.[^@]+$"  # Validação básica
    )
    
    company: str | None = Field(
        None,
        description="Nome da empresa mencionada. Ex: 'Clínica Saúde Plus'"
    )
    
    role: str | None = Field(
        None,
        description="Cargo/função mencionada. Ex: 'Dentista', 'Dono', 'Gerente'"
    )
    
    location: str | None = Field(
        None,
        description="Cidade/Estado mencionados. Ex: 'Maringá-PR'"
    )
    
    # ============================================================
    # INTERESSE E QUALIFICAÇÃO (extraídos pelo ExtractionAgent)
    # ============================================================
    
    primary_interest: Literal[
        "saas",
        "sob_medida",
        "gestao_perfis",
        "trafego_pago",
        "automacao_atendimento",
        "intermediacao"
    ] | None = Field(
        None,
        description="Interesse primário detectado (define contexto dinâmico do Otto)"
    )
    
    secondary_interests: list[str] = Field(
        default_factory=list,
        description="Outros interesses mencionados. Ex: ['saas', 'trafego_pago']"
    )
    
    urgency: Literal["low", "medium", "high", "urgent"] | None = Field(
        None,
        description="Urgência detectada na conversa"
    )
    
    budget_indication: str | None = Field(
        None,
        max_length=100,
        description="Indicação de orçamento mencionado. Ex: 'até R$ 500/mês', 'investimento de R$ 10k'"
    )
    
    specific_need: str | None = Field(
        None,
        max_length=200,
        description="Necessidade específica expressa. Ex: 'sistema para clínica com 3 dentistas'"
    )
    
    company_size: Literal["mei", "micro", "pequena", "media", "grande"] | None = Field(
        None,
        description="Porte da empresa (inferido se possível)"
    )
    
    # ============================================================
    # SCORES E QUALIFICAÇÃO (calculados automaticamente)
    # ============================================================
    
    qualification_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Score de qualificação 0-100 (calculado automaticamente)"
    )
    
    is_qualified: bool = Field(
        default=False,
        description="True se qualification_score >= 60"
    )
    
    # ============================================================
    # METADADOS DE INTERAÇÃO (rastreamento)
    # ============================================================
    
    first_contact_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp da primeira mensagem recebida"
    )
    
    last_updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Última atualização do LeadContact"
    )
    
    last_message_at: datetime | None = Field(
        None,
        description="Timestamp da última mensagem recebida"
    )
    
    total_messages: int = Field(
        default=0,
        ge=0,
        description="Total de mensagens trocadas nesta conversa"
    )
    
    # ============================================================
    # FLAGS DE ESTADO (controle de fluxo)
    # ============================================================
    
    requested_human: bool = Field(
        default=False,
        description="True se lead solicitou atendimento humano"
    )
    
    showed_objection: bool = Field(
        default=False,
        description="True se levantou objeção (preço, confiança, tempo, etc)"
    )
    
    was_notified_to_team: bool = Field(
        default=False,
        description="True se time comercial já foi notificado sobre este lead qualificado"
    )
    
    # ============================================================
    # METADATA ADICIONAL (JSON flexível)
    # ============================================================
    
    custom_metadata: dict = Field(
        default_factory=dict,
        description="Metadata flexível para dados adicionais. Ex: {'source': 'instagram', 'campaign': 'jan2026'}"
    )
    
    # ============================================================
    # MÉTODOS
    # ============================================================
    
    def calculate_qualification_score(self) -> float:
        """
        Calcula score de qualificação baseado em campos preenchidos.
        
        Critérios:
        - Nome real (full_name): +15
        - Contato adicional (email): +15
        - Empresa: +10
        - Interesse primário: +20
        - Necessidade específica: +15
        - Urgência alta/urgente: +15
        - Budget indication: +10
        
        Total possível: 100 pontos
        """
        score = 0.0
        
        if self.full_name:
            score += 15
        if self.email:
            score += 15
        if self.company:
            score += 10
        if self.primary_interest:
            score += 20
        if self.specific_need:
            score += 15
        if self.urgency in ["high", "urgent"]:
            score += 15
        if self.budget_indication:
            score += 10
        
        self.qualification_score = score
        self.is_qualified = score >= 60
        self.last_updated_at = datetime.utcnow()
        
        return score
    
    def to_prompt_summary(self) -> str:
        """
        Converte para texto resumido para injeção no prompt do Otto.
        
        Usado em: OttoAgent.process_message()
        Max: ~200 tokens
        """
        parts = []
        
        # Identificação (sempre presente)
        parts.append(f"**WhatsApp:** {self.whatsapp_name} ({self.phone})")
        
        # Nome real se diferente
        if self.full_name and self.full_name.lower() != self.whatsapp_name.lower():
            parts.append(f"**Nome Completo:** {self.full_name}")
        
        # Empresa
        if self.company:
            size_str = f" ({self.company_size})" if self.company_size else ""
            parts.append(f"**Empresa:** {self.company}{size_str}")
        
        # Cargo
        if self.role:
            parts.append(f"**Cargo:** {self.role}")
        
        # Contato adicional
        if self.email:
            parts.append(f"**Email:** {self.email}")
        
        # Interesse (CRÍTICO para context injection)
        if self.primary_interest:
            interest_display = self.primary_interest.replace("_", " ").title()
            parts.append(f"**Interesse Principal:** {interest_display}")
            
            if self.secondary_interests:
                secondary = ", ".join(i.replace("_", " ").title() for i in self.secondary_interests)
                parts.append(f"**Também mencionou:** {secondary}")
        else:
            parts.append("**Interesse:** Ainda não identificado claramente")
        
        # Necessidade específica
        if self.specific_need:
            parts.append(f"**Necessidade:** {self.specific_need}")
        
        # Urgência
        if self.urgency:
            urgency_map = {
                "low": "Baixa (pesquisando)",
                "medium": "Média (avaliando opções)",
                "high": "Alta (precisa em breve)",
                "urgent": "🚨 URGENTE (precisa agora)"
            }
            parts.append(f"**Urgência:** {urgency_map[self.urgency]}")
        
        # Budget
        if self.budget_indication:
            parts.append(f"**Orçamento mencionado:** {self.budget_indication}")
        
        # Score de qualificação
        emoji = "✅" if self.is_qualified else "⏳"
        status = "QUALIFICADO" if self.is_qualified else "Qualificando"
        parts.append(f"**Score:** {self.qualification_score:.0f}/100 {emoji} {status}")
        
        # Flags importantes
        alerts = []
        if self.requested_human:
            alerts.append("🙋 Solicitou atendimento humano")
        if self.showed_objection:
            alerts.append("⚠️ Levantou objeção")
        if self.is_qualified and not self.was_notified_to_team:
            alerts.append("🔔 LEAD QUALIFICADO (time ainda não notificado)")
        
        if alerts:
            parts.append(f"**Atenção:** {' | '.join(alerts)}")
        
        return "\n".join(parts)
    
    def to_firestore_dict(self) -> dict:
        """Converte para dict compatível com Firestore."""
        data = self.model_dump()
        # Firestore não aceita None, substitui por string vazia ou remove
        for key, value in list(data.items()):
            if value is None:
                del data[key]
        return data
    
    @classmethod
    def from_firestore_dict(cls, data: dict) -> "LeadContact":
        """Cria instância a partir de documento Firestore."""
        # Converte strings de datetime de volta
        if "first_contact_at" in data and isinstance(data["first_contact_at"], str):
            data["first_contact_at"] = datetime.fromisoformat(data["first_contact_at"])
        if "last_updated_at" in data and isinstance(data["last_updated_at"], str):
            data["last_updated_at"] = datetime.fromisoformat(data["last_updated_at"])
        if "last_message_at" in data and isinstance(data["last_message_at"], str):
            data["last_message_at"] = datetime.fromisoformat(data["last_message_at"])
        
        return cls(**data)
    
    @field_validator("phone", "wa_id")
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        """Valida formato de telefone internacional."""
        if not re.match(r"^\d{12,15}$", v):
            raise ValueError(f"Telefone deve ter 12-15 dígitos no formato internacional. Recebido: {v}")
        return v
```

***

## Firestore Storage Strategy

### Collection Structure
```
Firestore
└── lead_contacts/                    # Collection
    ├── {wa_id}/                      # Document ID = wa_id (ex: "5544988887777")
    │   ├── wa_id: "5544988887777"
    │   ├── phone: "5544988887777"
    │   ├── whatsapp_name: "João Silva"
    │   ├── full_name: "Dr. João Pedro Silva"
    │   ├── email: "joao@clinica.com"
    │   ├── company: "Clínica Saúde Plus"
    │   ├── primary_interest: "saas"
    │   ├── qualification_score: 65.0
    │   ├── is_qualified: true
    │   ├── first_contact_at: Timestamp(...)
    │   ├── last_updated_at: Timestamp(...)
    │   └── ...
    │
    └── {wa_id}/                      # Outro lead
        └── ...
```

### Indexes Necessários (Firestore)
```python
# Criar indexes compostos para queries eficientes

# Query 1: Buscar leads qualificados não notificados
# Collection: lead_contacts
# Fields: is_qualified (ASC), was_notified_to_team (ASC), qualification_score (DESC)

# Query 2: Buscar leads por interesse
# Collection: lead_contacts
# Fields: primary_interest (ASC), qualification_score (DESC), last_updated_at (DESC)

# Query 3: Buscar leads inativos (follow-up)
# Collection: lead_contacts
# Fields: last_message_at (ASC), is_qualified (ASC)
```

***

## Exemplo de Fluxo Completo

### 1. Webhook recebe primeira mensagem

**Payload WhatsApp:**
```json
{
  "contacts": [{
    "profile": {"name": "João Silva"},
    "wa_id": "5544988887777"
  }],
  "messages": [{
    "from": "5544988887777",
    "text": {"body": "Oi, preciso de um sistema para minha clínica"}
  }]
}
```

**LeadContact criado no Firestore:**
```python
LeadContact(
    wa_id="5544988887777",              # ← Do webhook
    phone="5544988887777",               # ← Do webhook (mesmo que wa_id)
    whatsapp_name="João Silva",          # ← Do webhook (contacts[0].profile.name)
    
    full_name=None,                      # Ainda não extraído
    email=None,                          # Ainda não extraído
    company=None,                        # Ainda não extraído
    
    primary_interest=None,               # ExtractionAgent vai preencher
    specific_need=None,                  # ExtractionAgent vai preencher
    
    qualification_score=0.0,             # Ainda não qualificado
    is_qualified=False,
    
    first_contact_at=datetime.utcnow(),
    last_updated_at=datetime.utcnow(),
    total_messages=1
)
```

***

### 2. ExtractionAgent processa a mensagem

**Input:** `"Oi, preciso de um sistema para minha clínica"`

**ExtractedLeadInfo:**
```python
ExtractedLeadInfo(
    name=None,                           # "João Silva" não é nome completo, é só primeiro nome
    email=None,
    phone=None,
    company=None,
    service_interest=["saas"],           # ← DETECTOU!
    specific_need="sistema para clínica", # ← DETECTOU!
    urgency="medium",
    extraction_confidence=0.85
)
```

**LeadContact atualizado (merge):**
```python
LeadContact(
    # Dados do webhook (não mudam)
    wa_id="5544988887777",
    phone="5544988887777",
    whatsapp_name="João Silva",
    
    # Extraídos agora
    primary_interest="saas",             # ← NOVO
    specific_need="sistema para clínica", # ← NOVO
    urgency="medium",                    # ← NOVO
    
    # Score recalculado
    qualification_score=35.0,            # (interest 20 + need 15)
    is_qualified=False,                  # Ainda não (precisa >= 60)
    
    total_messages=1,
    last_updated_at=datetime.utcnow()
)
```

***

### 3. Segunda mensagem: "Somos 3 dentistas, sou Dr. João Pedro"

**ExtractionAgent extrai:**
```python
ExtractedLeadInfo(
    name="Dr. João Pedro",               # ← CAPTUROU!
    role="dentista",
    service_interest=["saas"],
    specific_need="clínica com 3 dentistas",
    urgency="medium",
    extraction_confidence=0.92
)
```

**LeadContact atualizado:**
```python
LeadContact(
    # Dados do webhook (não mudam)
    wa_id="5544988887777",
    phone="5544988887777",
    whatsapp_name="João Silva",          # Nome do WhatsApp (não sobrescreve)
    
    # Extraídos
    full_name="Dr. João Pedro",          # ← NOVO (nome real diferente do WhatsApp)
    role="dentista",                     # ← NOVO
    
    primary_interest="saas",
    specific_need="clínica com 3 dentistas", # Atualizado
    urgency="medium",
    
    # Score recalculado
    qualification_score=60.0,            # (name 15 + interest 20 + need 15 + company inferida 10)
    is_qualified=True,                   # ← QUALIFICOU!
    
    total_messages=2,
    last_updated_at=datetime.utcnow()
)
```

***

### 4. Terceira mensagem: "Meu email é joao@clinica.com.br"

**ExtractionAgent extrai:**
```python
ExtractedLeadInfo(
    email="joao@clinica.com.br",         # ← CAPTUROU!
    service_interest=["saas"],
    extraction_confidence=0.95
)
```

**LeadContact atualizado:**
```python
LeadContact(
    # ... campos anteriores mantidos
    
    email="joao@clinica.com.br",         # ← NOVO
    
    # Score recalculado
    qualification_score=75.0,            # (+15 por email)
    is_qualified=True,
    
    total_messages=3,
    last_updated_at=datetime.utcnow()
)
```

***

## Resumo: O Que Armazenar no Banco

### ✅ Campos que VÊM DO WEBHOOK (sempre disponíveis)
- `wa_id` (ID único do usuário no WhatsApp)
- `phone` (número do telefone, igual ao `wa_id`)
- `whatsapp_name` (nome salvo no WhatsApp do usuário)

### ✅ Campos EXTRAÍDOS pelo ExtractionAgent (progressivamente)
- `full_name` (nome completo real, pode diferir do `whatsapp_name`)
- `email`
- `company`
- `role`
- `location`
- `primary_interest` ← **CRÍTICO para context injection**
- `secondary_interests`
- `urgency`
- `budget_indication`
- `specific_need`
- `company_size`

### ✅ Campos CALCULADOS automaticamente
- `qualification_score` (0-100)
- `is_qualified` (boolean)
- `first_contact_at`
- `last_updated_at`
- `last_message_at`
- `total_messages`

### ✅ Flags de CONTROLE
- `requested_human`
- `showed_objection`
- `was_notified_to_team`

**Document ID no Firestore:** `wa_id` (ex: `"5544988887777"`)

**Tamanho estimado por documento:** ~2-5KB

**TTL/Retenção:** Indefinido (leads são ativos permanentes, criar job de archiving para leads inativos 90+ dias)

Está claro agora? Precisa de ajuda com a implementação do repository pattern para Firestore ou está pronto para continuar com o TODO?