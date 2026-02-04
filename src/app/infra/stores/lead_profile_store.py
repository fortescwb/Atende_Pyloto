"""Implementações de store para LeadProfile.

Memory: Desenvolvimento e testes.
Redis: Staging e produção.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.domain.lead_profile import LeadProfile

logger = logging.getLogger(__name__)

# Prefixo para chaves no Redis
LEAD_PROFILE_PREFIX = "lead_profile:"
LEAD_PROFILE_INDEX = "lead_profiles:index"


class MemoryLeadProfileStore:
    """Store em memória para desenvolvimento/testes."""

    def __init__(self) -> None:
        self._profiles: dict[str, LeadProfile] = {}

    def get(self, phone: str) -> LeadProfile | None:
        """Busca perfil por telefone."""
        return self._profiles.get(phone)

    def save(self, profile: LeadProfile) -> None:
        """Salva ou atualiza perfil."""
        self._profiles[profile.phone] = profile
        logger.debug("lead_profile_saved", extra={"phone": profile.phone[:6] + "***"})

    def delete(self, phone: str) -> bool:
        """Remove perfil."""
        if phone in self._profiles:
            del self._profiles[phone]
            return True
        return False

    def list_all(self, limit: int = 100, offset: int = 0) -> list[LeadProfile]:
        """Lista todos os perfis."""
        profiles = list(self._profiles.values())
        return profiles[offset : offset + limit]

    def search_by_name(self, name: str) -> list[LeadProfile]:
        """Busca por nome."""
        name_lower = name.lower()
        return [
            p
            for p in self._profiles.values()
            if p.name and name_lower in p.name.lower()
            or p.surname and name_lower in p.surname.lower()
        ]

    def count(self) -> int:
        """Retorna quantidade total."""
        return len(self._profiles)

    # Métodos async (para compatibilidade)
    async def get_async(self, phone: str) -> LeadProfile | None:
        return self.get(phone)

    async def save_async(self, profile: LeadProfile) -> None:
        self.save(profile)

    async def delete_async(self, phone: str) -> bool:
        return self.delete(phone)

    async def list_all_async(
        self, limit: int = 100, offset: int = 0
    ) -> list[LeadProfile]:
        return self.list_all(limit, offset)

    async def get_or_create_async(self, phone: str) -> LeadProfile:
        """Busca ou cria novo perfil."""
        profile = self.get(phone)
        if profile is None:
            profile = LeadProfile.create_new(phone)
            self.save(profile)
            logger.info(
                "lead_profile_created", extra={"phone": phone[:6] + "***"}
            )
        return profile


class RedisLeadProfileStore:
    """Store Redis para staging/produção.

    Estrutura:
    - lead_profile:{phone} → JSON do perfil
    - lead_profiles:index → SET com todos os phones
    """

    def __init__(
        self,
        redis_client: Any,
        async_client: Any | None = None,
    ) -> None:
        self._redis = redis_client
        self._async_redis = async_client

    def _key(self, phone: str) -> str:
        """Gera chave Redis para o phone."""
        return f"{LEAD_PROFILE_PREFIX}{phone}"

    def get(self, phone: str) -> LeadProfile | None:
        """Busca perfil por telefone."""
        data = self._redis.get(self._key(phone))
        if data:
            try:
                data_str = data if isinstance(data, str) else data.decode()
                return LeadProfile.from_json(data_str)
            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                logger.warning(
                    "lead_profile_parse_error",
                    extra={"phone": phone[:6] + "***", "error": str(e)},
                )
        return None

    def save(self, profile: LeadProfile) -> None:
        """Salva ou atualiza perfil."""
        self._redis.set(self._key(profile.phone), profile.to_json())
        self._redis.sadd(LEAD_PROFILE_INDEX, profile.phone)
        logger.debug("lead_profile_saved", extra={"phone": profile.phone[:6] + "***"})

    def delete(self, phone: str) -> bool:
        """Remove perfil."""
        deleted = self._redis.delete(self._key(phone))
        self._redis.srem(LEAD_PROFILE_INDEX, phone)
        return bool(deleted)

    def list_all(self, limit: int = 100, offset: int = 0) -> list[LeadProfile]:
        """Lista todos os perfis."""
        phones_set = self._redis.smembers(LEAD_PROFILE_INDEX)
        phones = list(phones_set) if phones_set else []
        phones = phones[offset : offset + limit]
        profiles = []
        for phone in phones:
            phone_str = phone if isinstance(phone, str) else phone.decode()
            profile = self.get(phone_str)
            if profile:
                profiles.append(profile)
        return profiles

    def search_by_name(self, name: str) -> list[LeadProfile]:
        """Busca por nome (varredura completa, usar com cuidado)."""
        name_lower = name.lower()
        results = []
        for profile in self.list_all(limit=1000):
            if (profile.name and name_lower in profile.name.lower()) or (
                profile.surname and name_lower in profile.surname.lower()
            ):
                results.append(profile)
        return results

    def count(self) -> int:
        """Retorna quantidade total."""
        result = self._redis.scard(LEAD_PROFILE_INDEX)
        return int(result) if result else 0

    # Métodos async
    async def get_async(self, phone: str) -> LeadProfile | None:
        """Busca perfil (async)."""
        if self._async_redis:
            data = await self._async_redis.get(self._key(phone))
            if data:
                try:
                    return LeadProfile.from_json(
                        data if isinstance(data, str) else data.decode()
                    )
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(
                        "lead_profile_parse_error",
                        extra={"phone": phone[:6] + "***", "error": str(e)},
                    )
            return None
        return self.get(phone)

    async def save_async(self, profile: LeadProfile) -> None:
        """Salva perfil (async)."""
        if self._async_redis:
            await self._async_redis.set(self._key(profile.phone), profile.to_json())
            await self._async_redis.sadd(LEAD_PROFILE_INDEX, profile.phone)
            logger.debug(
                "lead_profile_saved", extra={"phone": profile.phone[:6] + "***"}
            )
        else:
            self.save(profile)

    async def delete_async(self, phone: str) -> bool:
        """Remove perfil (async)."""
        if self._async_redis:
            deleted = await self._async_redis.delete(self._key(phone))
            await self._async_redis.srem(LEAD_PROFILE_INDEX, phone)
            return bool(deleted)
        return self.delete(phone)

    async def list_all_async(
        self, limit: int = 100, offset: int = 0
    ) -> list[LeadProfile]:
        """Lista perfis (async)."""
        if self._async_redis:
            phones = list(await self._async_redis.smembers(LEAD_PROFILE_INDEX))
            phones = phones[offset : offset + limit]
            profiles = []
            for phone in phones:
                phone_str = phone if isinstance(phone, str) else phone.decode()
                profile = await self.get_async(phone_str)
                if profile:
                    profiles.append(profile)
            return profiles
        return self.list_all(limit, offset)

    async def get_or_create_async(self, phone: str) -> LeadProfile:
        """Busca ou cria novo perfil (async)."""
        profile = await self.get_async(phone)
        if profile is None:
            profile = LeadProfile.create_new(phone)
            await self.save_async(profile)
            logger.info("lead_profile_created", extra={"phone": phone[:6] + "***"})
        return profile
