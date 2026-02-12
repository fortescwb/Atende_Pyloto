"""Settings de integracao com Google Calendar.

Centralizar a leitura de env aqui evita espalhar parse de configuracao
pela aplicacao e reduz risco de divergencia entre servicos.
"""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field


class CalendarSettings(BaseModel):
    """Configuracoes de calendar usadas pelo dominio de agendamentos."""

    model_config = ConfigDict(extra="ignore")

    google_calendar_id: str = Field(
        default="",
        description="ID do calendario alvo no Google Calendar.",
    )
    google_service_account_json: str | None = Field(
        default=None,
        description="Credencial JSON da service account em formato texto.",
    )
    calendar_timezone: str = Field(
        default="America/Sao_Paulo",
        description="Timezone base para operacoes de agenda.",
    )
    calendar_slot_duration_min: int = Field(
        default=30,
        ge=1,
        description="Duracao padrao de um slot em minutos.",
    )
    calendar_buffer_between_events_min: int = Field(
        default=15,
        ge=0,
        description="Intervalo minimo entre eventos em minutos.",
    )
    calendar_business_start_hour: int = Field(
        default=9,
        ge=0,
        le=23,
        description="Hora de inicio do expediente para ofertas de horario.",
    )
    calendar_business_end_hour: int = Field(
        default=17,
        ge=0,
        le=23,
        description="Hora de fim do expediente para ofertas de horario.",
    )
    calendar_enabled: bool = Field(
        default=False,
        description="Feature flag para habilitar integracao real com calendario.",
    )


def _read_optional_env(key: str) -> str | None:
    """Retorna valor opcional da env sem propagar string vazia."""
    raw_value = os.getenv(key)
    if raw_value is None:
        return None
    stripped_value = raw_value.strip()
    return stripped_value or None


def _parse_bool(value: str) -> bool:
    """Converte texto de env em bool com o mesmo padrao dos outros settings."""
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_calendar_from_env() -> CalendarSettings:
    """Carrega CalendarSettings a partir de variaveis de ambiente."""
    return CalendarSettings(
        google_calendar_id=os.getenv("GOOGLE_CALENDAR_ID", ""),
        google_service_account_json=_read_optional_env("GOOGLE_SERVICE_ACCOUNT_JSON"),
        calendar_timezone=os.getenv("CALENDAR_TIMEZONE", "America/Sao_Paulo"),
        calendar_slot_duration_min=int(os.getenv("CALENDAR_SLOT_DURATION_MIN", "30")),
        calendar_buffer_between_events_min=int(
            os.getenv("CALENDAR_BUFFER_BETWEEN_EVENTS_MIN", "15")
        ),
        calendar_business_start_hour=int(os.getenv("CALENDAR_BUSINESS_START_HOUR", "9")),
        calendar_business_end_hour=int(os.getenv("CALENDAR_BUSINESS_END_HOUR", "17")),
        calendar_enabled=_parse_bool(os.getenv("CALENDAR_ENABLED", "false")),
    )


@lru_cache(maxsize=1)
def get_calendar_settings() -> CalendarSettings:
    """Retorna instancia cacheada de CalendarSettings."""
    return _load_calendar_from_env()


__all__ = ["CalendarSettings", "get_calendar_settings"]
