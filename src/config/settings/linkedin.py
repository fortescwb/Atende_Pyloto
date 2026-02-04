"""Settings específicas de LinkedIn.

Configurações do canal LinkedIn via LinkedIn API.

TODO: Implementar quando canal LinkedIn for desenvolvido.
Referência: WhatsApp settings em config/settings/whatsapp.py
"""

from __future__ import annotations

# from dataclasses import dataclass
# from functools import lru_cache
# import os

# Constantes da LinkedIn API
# LINKEDIN_API_VERSION: str = "v2"
# LINKEDIN_API_BASE_URL: str = "https://api.linkedin.com"


# @dataclass(frozen=True)
# class LinkedInSettings:
#     """Configurações do canal LinkedIn.
#
#     Attributes:
#         access_token: Token de acesso OAuth 2.0
#         client_id: Client ID do app LinkedIn
#         client_secret: Client Secret do app LinkedIn
#         organization_id: ID da organização (company page)
#         api_version: Versão da API
#         api_base_url: URL base da API
#         request_timeout_seconds: Timeout para requisições HTTP
#         max_retries: Máximo de tentativas em caso de erro
#     """
#
#     # Credenciais OAuth
#     access_token: str = ""
#     client_id: str = ""
#     client_secret: str = ""
#     organization_id: str = ""
#
#     # API
#     api_version: str = LINKEDIN_API_VERSION
#     api_base_url: str = LINKEDIN_API_BASE_URL
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
#         """Valida configurações mínimas de LinkedIn."""
#         errors: list[str] = []
#         if not self.access_token:
#             errors.append("LINKEDIN_ACCESS_TOKEN não configurado")
#         if not self.organization_id:
#             errors.append("LINKEDIN_ORGANIZATION_ID não configurado")
#         return errors


# def _load_from_env() -> LinkedInSettings:
#     """Carrega LinkedInSettings de variáveis de ambiente."""
#     return LinkedInSettings(
#         access_token=os.getenv("LINKEDIN_ACCESS_TOKEN", ""),
#         client_id=os.getenv("LINKEDIN_CLIENT_ID", ""),
#         client_secret=os.getenv("LINKEDIN_CLIENT_SECRET", ""),
#         organization_id=os.getenv("LINKEDIN_ORGANIZATION_ID", ""),
#         api_version=os.getenv("LINKEDIN_API_VERSION", LINKEDIN_API_VERSION),
#         api_base_url=os.getenv("LINKEDIN_API_BASE_URL", LINKEDIN_API_BASE_URL),
#         request_timeout_seconds=float(
#             os.getenv("LINKEDIN_REQUEST_TIMEOUT_SECONDS", "30")
#         ),
#         max_retries=int(os.getenv("LINKEDIN_MAX_RETRIES", "3")),
#     )


# @lru_cache(maxsize=1)
# def get_linkedin_settings() -> LinkedInSettings:
#     """Retorna instância cacheada de LinkedInSettings."""
#     return _load_from_env()
