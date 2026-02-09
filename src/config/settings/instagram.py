"""Settings específicas de Instagram.

Configurações do canal Instagram via Graph API (Meta).

Pendente: ativar quando canal Instagram for desenvolvido.
Referência: WhatsApp settings em config/settings/whatsapp.py
"""

from __future__ import annotations

# from dataclasses import dataclass
# from functools import lru_cache
# import os

# Constantes da Graph API para Instagram
# INSTAGRAM_API_VERSION: str = "v24.0"
# INSTAGRAM_API_BASE_URL: str = "https://graph.facebook.com"


# @dataclass(frozen=True)
# class InstagramSettings:
#     """Configurações do canal Instagram.
#
#     Attributes:
#         access_token: Token de acesso à Graph API
#         business_account_id: ID da conta de negócios Instagram
#         api_version: Versão da Graph API
#         api_base_url: URL base da Graph API
#         request_timeout_seconds: Timeout para requisições HTTP
#         max_retries: Máximo de tentativas em caso de erro
#     """
#
#     # Credenciais
#     access_token: str = ""
#     business_account_id: str = ""
#
#     # API
#     api_version: str = INSTAGRAM_API_VERSION
#     api_base_url: str = INSTAGRAM_API_BASE_URL
#
#     # Timeouts e retries
#     request_timeout_seconds: float = 30.0
#     max_retries: int = 3
#
#     @property
#     def api_endpoint(self) -> str:
#         """URL base completa da API com versão."""
#         return f"{self.api_base_url}/{self.api_version}"
#
#     def validate(self) -> list[str]:
#         """Valida configurações mínimas de Instagram."""
#         errors: list[str] = []
#         if not self.business_account_id:
#             errors.append("INSTAGRAM_BUSINESS_ACCOUNT_ID não configurado")
#         if not self.access_token:
#             errors.append("INSTAGRAM_ACCESS_TOKEN não configurado")
#         return errors


# def _load_from_env() -> InstagramSettings:
#     """Carrega InstagramSettings de variáveis de ambiente."""
#     return InstagramSettings(
#         access_token=os.getenv("INSTAGRAM_ACCESS_TOKEN", ""),
#         business_account_id=os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", ""),
#         api_version=os.getenv("INSTAGRAM_API_VERSION", INSTAGRAM_API_VERSION),
#         api_base_url=os.getenv("INSTAGRAM_API_BASE_URL", INSTAGRAM_API_BASE_URL),
#         request_timeout_seconds=float(
#             os.getenv("INSTAGRAM_REQUEST_TIMEOUT_SECONDS", "30")
#         ),
#         max_retries=int(os.getenv("INSTAGRAM_MAX_RETRIES", "3")),
#     )


# @lru_cache(maxsize=1)
# def get_instagram_settings() -> InstagramSettings:
#     """Retorna instância cacheada de InstagramSettings."""
#     return _load_from_env()
