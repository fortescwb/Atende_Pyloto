"""Settings específicas de Facebook.

Configurações do canal Facebook Messenger via Graph API (Meta).

Pendente: ativar quando canal Facebook for desenvolvido.
Referência: WhatsApp settings em config/settings/whatsapp.py
"""

from __future__ import annotations

# from dataclasses import dataclass
# from functools import lru_cache
# import os

# Constantes da Graph API para Facebook
# FACEBOOK_API_VERSION: str = "v24.0"
# FACEBOOK_API_BASE_URL: str = "https://graph.facebook.com"


# @dataclass(frozen=True)
# class FacebookSettings:
#     """Configurações do canal Facebook Messenger.
#
#     Attributes:
#         page_access_token: Token de acesso da página
#         page_id: ID da página do Facebook
#         app_secret: Secret do app para validação de webhooks
#         verify_token: Token para verificação de webhook
#         api_version: Versão da Graph API
#         api_base_url: URL base da Graph API
#         request_timeout_seconds: Timeout para requisições HTTP
#         max_retries: Máximo de tentativas em caso de erro
#     """
#
#     # Credenciais
#     page_access_token: str = ""
#     page_id: str = ""
#     app_secret: str = ""
#     verify_token: str = ""
#
#     # API
#     api_version: str = FACEBOOK_API_VERSION
#     api_base_url: str = FACEBOOK_API_BASE_URL
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
#     def get_messages_endpoint(self) -> str:
#         """Retorna URL para envio de mensagens."""
#         return f"{self.api_endpoint}/me/messages"
#
#     def validate(self) -> list[str]:
#         """Valida configurações mínimas de Facebook."""
#         errors: list[str] = []
#         if not self.page_id:
#             errors.append("FACEBOOK_PAGE_ID não configurado")
#         if not self.page_access_token:
#             errors.append("FACEBOOK_PAGE_ACCESS_TOKEN não configurado")
#         return errors


# def _load_from_env() -> FacebookSettings:
#     """Carrega FacebookSettings de variáveis de ambiente."""
#     return FacebookSettings(
#         page_access_token=os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", ""),
#         page_id=os.getenv("FACEBOOK_PAGE_ID", ""),
#         app_secret=os.getenv("FACEBOOK_APP_SECRET", ""),
#         verify_token=os.getenv("FACEBOOK_VERIFY_TOKEN", ""),
#         api_version=os.getenv("FACEBOOK_API_VERSION", FACEBOOK_API_VERSION),
#         api_base_url=os.getenv("FACEBOOK_API_BASE_URL", FACEBOOK_API_BASE_URL),
#         request_timeout_seconds=float(
#             os.getenv("FACEBOOK_REQUEST_TIMEOUT_SECONDS", "30")
#         ),
#         max_retries=int(os.getenv("FACEBOOK_MAX_RETRIES", "3")),
#     )


# @lru_cache(maxsize=1)
# def get_facebook_settings() -> FacebookSettings:
#     """Retorna instância cacheada de FacebookSettings."""
#     return _load_from_env()
