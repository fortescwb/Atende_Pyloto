"""LeadProfile — Modelo de perfil de lead/contato.

Estrutura persistente para armazenar informações de cada contato.
Identificador único: número de telefone (E.164).

Campos:
- Dados pessoais (nome, sobrenome, endereço)
- Informações pessoais (texto livre, até 1500 chars)
- Até 3 necessidades ativas

Persistência: Firestore/Redis conforme ambiente.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class NeedStatus(Enum):
    """Status de uma necessidade."""

    ACTIVE = "active"  # Em andamento
    COMPLETED = "completed"  # Concluída/vendida
    CANCELLED = "cancelled"  # Cancelada/desistiu
    ON_HOLD = "on_hold"  # Pausada


class NeedType(Enum):
    """Tipos de necessidade/serviço."""

    SAAS = "saas"  # SaaS Adaptável
    CUSTOM_SYSTEM = "custom_system"  # Sistema sob medida
    WEBSITE = "website"  # Site institucional
    LANDING_PAGE = "landing_page"  # Landing page
    TRAFFIC_MANAGEMENT = "traffic_management"  # Gestão de tráfego
    AUTOMATION = "automation"  # Automação
    DELIVERY_SERVICE = "delivery_service"  # Entregas/serviços
    OTHER = "other"  # Outro


@dataclass
class Address:
    """Endereço do lead."""

    street: str | None = None
    number: str | None = None
    complement: str | None = None
    neighborhood: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str = "BR"

    def is_complete(self) -> bool:
        """Verifica se endereço tem dados mínimos."""
        return bool(self.city and self.state)

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "street": self.street,
            "number": self.number,
            "complement": self.complement,
            "neighborhood": self.neighborhood,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "country": self.country,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Address:
        """Cria a partir de dicionário."""
        return cls(
            street=data.get("street"),
            number=data.get("number"),
            complement=data.get("complement"),
            neighborhood=data.get("neighborhood"),
            city=data.get("city"),
            state=data.get("state"),
            zip_code=data.get("zip_code"),
            country=data.get("country", "BR"),
        )


@dataclass
class Need:
    """Necessidade/demanda do lead.

    Campos importantes:
    - is_current: marca se esta é a solicitação sendo tratada AGORA
    - status: ACTIVE (ativa), COMPLETED (atendida), CANCELLED, ON_HOLD
    """

    need_type: NeedType
    title: str  # Resumo curto (ex: "Sistema para clínica odontológica")
    details: str = ""  # Detalhes coletados (até 2000 chars)
    status: NeedStatus = NeedStatus.ACTIVE
    is_current: bool = False  # True = esta é a solicitação sendo tratada AGORA
    budget_range: str | None = None  # Ex: "R$ 5.000 - R$ 10.000"
    urgency: str | None = None  # alta/média/baixa
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        now = datetime.utcnow().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def update_details(self, new_info: str) -> None:
        """Adiciona informação aos detalhes (máx 2000 chars)."""
        if self.details:
            self.details = f"{self.details}\n{new_info}"
        else:
            self.details = new_info
        self.details = self.details[:2000]
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "need_type": self.need_type.value,
            "title": self.title,
            "details": self.details,
            "status": self.status.value,
            "is_current": self.is_current,
            "budget_range": self.budget_range,
            "urgency": self.urgency,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Need:
        """Cria a partir de dicionário."""
        return cls(
            need_type=NeedType(data.get("need_type", "other")),
            title=data.get("title", ""),
            details=data.get("details", ""),
            status=NeedStatus(data.get("status", "active")),
            is_current=data.get("is_current", False),
            budget_range=data.get("budget_range"),
            urgency=data.get("urgency"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


MAX_ACTIVE_NEEDS = 3
MAX_PERSONAL_INFO_CHARS = 1500


@dataclass
class LeadProfile:
    """Perfil completo de um lead/contato.

    Identificador único: phone (formato E.164, ex: +5541988991078)
    """

    phone: str  # Identificador único (E.164)
    name: str | None = None
    surname: str | None = None
    email: str | None = None
    company: str | None = None
    address: Address = field(default_factory=Address)
    personal_info: str = ""  # Informações pessoais (até 1500 chars)
    needs: list[Need] = field(default_factory=list)

    # Metadata
    created_at: str = ""
    updated_at: str = ""
    last_contact_at: str = ""
    total_messages: int = 0
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        now = datetime.utcnow().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if not self.last_contact_at:
            self.last_contact_at = now

    @property
    def full_name(self) -> str:
        """Retorna nome completo."""
        parts = [p for p in [self.name, self.surname] if p]
        return " ".join(parts) if parts else ""

    @property
    def active_needs(self) -> list[Need]:
        """Retorna apenas necessidades ativas."""
        return [n for n in self.needs if n.status == NeedStatus.ACTIVE]

    def update_personal_info(self, new_info: str) -> None:
        """Atualiza informações pessoais (substituição inteligente).

        O agente deve enviar o texto atualizado completo,
        não apenas o delta.
        """
        self.personal_info = new_info[:MAX_PERSONAL_INFO_CHARS]
        self._touch()

    def add_need(self, need: Need, set_as_current: bool = True) -> bool:
        """Adiciona nova necessidade (máx 3 ativas).

        Args:
            need: Necessidade a adicionar
            set_as_current: Se True, marca esta como a solicitação atual

        Returns:
            True se adicionou, False se limite atingido.
        """
        if len(self.active_needs) >= MAX_ACTIVE_NEEDS:
            return False

        if set_as_current:
            # Desmarca outras como current
            for n in self.needs:
                n.is_current = False
            need.is_current = True

        self.needs.append(need)
        self._touch()
        return True

    def set_current_need(self, index: int) -> bool:
        """Define qual necessidade é a solicitação ATUAL.

        Apenas uma necessidade pode ser 'current' por vez.
        """
        if 0 <= index < len(self.needs):
            for i, need in enumerate(self.needs):
                need.is_current = i == index
            self._touch()
            return True
        return False

    @property
    def current_need(self) -> Need | None:
        """Retorna a necessidade marcada como atual."""
        return next((n for n in self.needs if n.is_current and n.status == NeedStatus.ACTIVE), None)

    def update_need(self, index: int, **kwargs: Any) -> bool:
        """Atualiza uma necessidade existente."""
        if 0 <= index < len(self.needs):
            need = self.needs[index]
            for key, value in kwargs.items():
                if hasattr(need, key):
                    setattr(need, key, value)
            need.updated_at = datetime.utcnow().isoformat()
            self._touch()
            return True
        return False

    def record_contact(self) -> None:
        """Registra um novo contato/mensagem."""
        self.last_contact_at = datetime.utcnow().isoformat()
        self.total_messages += 1
        self._touch()

    def _touch(self) -> None:
        """Atualiza timestamp de modificação."""
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário (para persistência)."""
        return {
            "phone": self.phone,
            "name": self.name,
            "surname": self.surname,
            "email": self.email,
            "company": self.company,
            "address": self.address.to_dict(),
            "personal_info": self.personal_info,
            "needs": [n.to_dict() for n in self.needs],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_contact_at": self.last_contact_at,
            "total_messages": self.total_messages,
            "tags": self.tags,
        }

    def to_json(self) -> str:
        """Serializa para JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_prompt_context(self) -> str:
        """Gera contexto formatado para prompts de IA."""
        lines = [f"Telefone: {self.phone}"]

        if self.full_name:
            lines.append(f"Nome: {self.full_name}")
        else:
            lines.append("Nome: (não informado)")

        if self.email:
            lines.append(f"Email: {self.email}")
        if self.company:
            lines.append(f"Empresa: {self.company}")

        if self.address.is_complete():
            lines.append(f"Cidade: {self.address.city}/{self.address.state}")

        if self.personal_info:
            lines.append(f"Informações: {self.personal_info[:500]}")

        # Necessidades organizadas por status
        current_need = next((n for n in self.needs if n.is_current and n.status == NeedStatus.ACTIVE), None)
        other_active = [n for n in self.active_needs if not n.is_current]
        completed = [n for n in self.needs if n.status == NeedStatus.COMPLETED]

        if current_need:
            lines.append("")
            lines.append(">>> SOLICITAÇÃO ATUAL (foco da conversa):")
            lines.append(f"    {current_need.title} ({current_need.need_type.value})")
            if current_need.details:
                lines.append(f"    Detalhes: {current_need.details[:300]}")
            if current_need.budget_range:
                lines.append(f"    Orçamento: {current_need.budget_range}")
            if current_need.urgency:
                lines.append(f"    Urgência: {current_need.urgency}")

        if other_active:
            lines.append("")
            lines.append("Outras necessidades ativas (futuras/paralelas):")
            for need in other_active:
                lines.append(f"  - {need.title} ({need.need_type.value})")

        if completed:
            lines.append("")
            lines.append("Histórico (já atendidas):")
            for need in completed[:3]:  # Máx 3 para não poluir
                lines.append(f"  ✓ {need.title}")

        return "\n".join(lines)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LeadProfile:
        """Cria a partir de dicionário."""
        address_data = data.get("address", {})
        needs_data = data.get("needs", [])

        return cls(
            phone=data["phone"],
            name=data.get("name"),
            surname=data.get("surname"),
            email=data.get("email"),
            company=data.get("company"),
            address=Address.from_dict(address_data) if address_data else Address(),
            personal_info=data.get("personal_info", ""),
            needs=[Need.from_dict(n) for n in needs_data],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            last_contact_at=data.get("last_contact_at", ""),
            total_messages=data.get("total_messages", 0),
            tags=data.get("tags", []),
        )

    @classmethod
    def from_json(cls, json_str: str) -> LeadProfile:
        """Deserializa de JSON."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def create_new(cls, phone: str) -> LeadProfile:
        """Cria novo perfil apenas com telefone."""
        return cls(phone=phone)
