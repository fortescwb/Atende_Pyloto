"""Protocolo para persistência de LeadProfile.

Define contrato para stores de LeadProfile.
Implementações: Redis, Firestore, Memory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.lead_profile import LeadProfile


class LeadProfileStoreProtocol(Protocol):
    """Contrato para store de LeadProfile."""

    def get(self, phone: str) -> LeadProfile | None:
        """Busca perfil por telefone.

        Args:
            phone: Número em formato E.164 (ex: +5541988991078)

        Returns:
            LeadProfile se existir, None caso contrário.
        """
        ...

    def save(self, profile: LeadProfile) -> None:
        """Salva ou atualiza perfil.

        Args:
            profile: Perfil a ser salvo.
        """
        ...

    def delete(self, phone: str) -> bool:
        """Remove perfil.

        Args:
            phone: Número do perfil a remover.

        Returns:
            True se removido, False se não existia.
        """
        ...

    def list_all(self, limit: int = 100, offset: int = 0) -> list[LeadProfile]:
        """Lista todos os perfis (paginado).

        Args:
            limit: Máximo de resultados.
            offset: Offset para paginação.

        Returns:
            Lista de perfis.
        """
        ...

    def search_by_name(self, name: str) -> list[LeadProfile]:
        """Busca perfis por nome (parcial).

        Args:
            name: Termo de busca.

        Returns:
            Lista de perfis que contém o termo no nome.
        """
        ...

    def count(self) -> int:
        """Retorna quantidade total de perfis."""
        ...


class AsyncLeadProfileStoreProtocol(Protocol):
    """Contrato assíncrono para store de LeadProfile."""

    async def get_async(self, phone: str) -> LeadProfile | None:
        """Busca perfil por telefone (async)."""
        ...

    async def save_async(self, profile: LeadProfile) -> None:
        """Salva ou atualiza perfil (async)."""
        ...

    async def delete_async(self, phone: str) -> bool:
        """Remove perfil (async)."""
        ...

    async def list_all_async(
        self, limit: int = 100, offset: int = 0
    ) -> list[LeadProfile]:
        """Lista todos os perfis (async)."""
        ...

    async def get_or_create_async(self, phone: str) -> LeadProfile:
        """Busca perfil ou cria novo se não existir.

        Args:
            phone: Número em formato E.164.

        Returns:
            Perfil existente ou novo.
        """
        ...
