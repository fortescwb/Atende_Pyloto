"""Settings específicas de Google Calendar.

Configurações do canal Google Calendar via Google Calendar API.

TODO: Implementar quando canal Google Calendar for desenvolvido.
Referência: WhatsApp settings em config/settings/whatsapp.py
"""

from __future__ import annotations

# from dataclasses import dataclass
# from functools import lru_cache
# import os

# Constantes da Google Calendar API
# GOOGLE_CALENDAR_API_VERSION: str = "v3"
# GOOGLE_CALENDAR_API_BASE_URL: str = "https://www.googleapis.com/calendar"


# @dataclass(frozen=True)
# class GoogleCalendarSettings:
#     """Configurações do canal Google Calendar.
#
#     Attributes:
#         client_id: Client ID do app Google
#         client_secret: Client Secret do app Google
#         access_token: Token de acesso OAuth 2.0
#         refresh_token: Refresh Token OAuth 2.0
#         calendar_id: ID do calendário padrão (geralmente 'primary')
#         api_version: Versão da API
#         api_base_url: URL base da API
#         request_timeout_seconds: Timeout para requisições HTTP
#         max_retries: Máximo de tentativas em caso de erro
#     """
#
#     # Credenciais OAuth
#     client_id: str = ""
#     client_secret: str = ""
#     access_token: str = ""
#     refresh_token: str = ""
#
#     # Calendário
#     calendar_id: str = "primary"
#
#     # API
#     api_version: str = GOOGLE_CALENDAR_API_VERSION
#     api_base_url: str = GOOGLE_CALENDAR_API_BASE_URL
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
#         """Valida configurações mínimas de Google Calendar."""
#         errors: list[str] = []
#         if not self.access_token and not self.refresh_token:
#             errors.append(
#                 "GOOGLE_CALENDAR_ACCESS_TOKEN ou REFRESH_TOKEN não configurado"
#             )
#         return errors


# def _load_from_env() -> GoogleCalendarSettings:
#     """Carrega GoogleCalendarSettings de variáveis de ambiente."""
#     return GoogleCalendarSettings(
#         client_id=os.getenv("GOOGLE_CALENDAR_CLIENT_ID", ""),
#         client_secret=os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET", ""),
#         access_token=os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN", ""),
#         refresh_token=os.getenv("GOOGLE_CALENDAR_REFRESH_TOKEN", ""),
#         calendar_id=os.getenv("GOOGLE_CALENDAR_ID", "primary"),
#         api_version=os.getenv(
#             "GOOGLE_CALENDAR_API_VERSION", GOOGLE_CALENDAR_API_VERSION
#         ),
#         api_base_url=os.getenv(
#             "GOOGLE_CALENDAR_API_BASE_URL", GOOGLE_CALENDAR_API_BASE_URL
#         ),
#         request_timeout_seconds=float(
#             os.getenv("GOOGLE_CALENDAR_REQUEST_TIMEOUT_SECONDS", "30")
#         ),
#         max_retries=int(os.getenv("GOOGLE_CALENDAR_MAX_RETRIES", "3")),
#     )


# @lru_cache(maxsize=1)
# def get_google_calendar_settings() -> GoogleCalendarSettings:
#     """Retorna instância cacheada de GoogleCalendarSettings."""
#     return _load_from_env()
