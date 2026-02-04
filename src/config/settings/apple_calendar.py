"""Settings específicas de Apple Calendar (CalDAV).

Configurações do canal Apple Calendar via CalDAV/iCloud.

TODO: Implementar quando canal Apple Calendar for desenvolvido.
Referência: WhatsApp settings em config/settings/whatsapp.py
"""

from __future__ import annotations

# from dataclasses import dataclass
# from functools import lru_cache
# import os

# Constantes do Apple CalDAV
# APPLE_CALDAV_BASE_URL: str = "https://caldav.icloud.com"


# @dataclass(frozen=True)
# class AppleCalendarSettings:
#     """Configurações do canal Apple Calendar (CalDAV).
#
#     Attributes:
#         apple_id: Apple ID (email)
#         app_specific_password: Senha específica de app (gerada em appleid.apple.com)
#         caldav_url: URL do servidor CalDAV
#         calendar_name: Nome do calendário padrão
#         request_timeout_seconds: Timeout para requisições HTTP
#         max_retries: Máximo de tentativas em caso de erro
#     """
#
#     # Credenciais
#     apple_id: str = ""
#     app_specific_password: str = ""
#
#     # CalDAV
#     caldav_url: str = APPLE_CALDAV_BASE_URL
#     calendar_name: str = "Calendar"
#
#     # Timeouts e retries
#     request_timeout_seconds: float = 30.0
#     max_retries: int = 3
#
#     def validate(self) -> list[str]:
#         """Valida configurações mínimas de Apple Calendar."""
#         errors: list[str] = []
#         if not self.apple_id:
#             errors.append("APPLE_CALENDAR_APPLE_ID não configurado")
#         if not self.app_specific_password:
#             errors.append("APPLE_CALENDAR_APP_SPECIFIC_PASSWORD não configurado")
#         return errors


# def _load_from_env() -> AppleCalendarSettings:
#     """Carrega AppleCalendarSettings de variáveis de ambiente."""
#     return AppleCalendarSettings(
#         apple_id=os.getenv("APPLE_CALENDAR_APPLE_ID", ""),
#         app_specific_password=os.getenv("APPLE_CALENDAR_APP_SPECIFIC_PASSWORD", ""),
#         caldav_url=os.getenv("APPLE_CALENDAR_CALDAV_URL", APPLE_CALDAV_BASE_URL),
#         calendar_name=os.getenv("APPLE_CALENDAR_NAME", "Calendar"),
#         request_timeout_seconds=float(
#             os.getenv("APPLE_CALENDAR_REQUEST_TIMEOUT_SECONDS", "30")
#         ),
#         max_retries=int(os.getenv("APPLE_CALENDAR_MAX_RETRIES", "3")),
#     )


# @lru_cache(maxsize=1)
# def get_apple_calendar_settings() -> AppleCalendarSettings:
#     """Retorna instância cacheada de AppleCalendarSettings."""
#     return _load_from_env()
