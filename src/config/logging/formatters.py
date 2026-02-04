"""Formatters de logging estruturado.

Define formatters para logs JSON com campos obrigatórios:
- correlation_id
- service
- timestamp (asctime)
- level
- logger (name)
- message

Conforme REGRAS_E_PADROES.md: logs estruturados, sem PII.
"""

from __future__ import annotations

from pythonjsonlogger.json import JsonFormatter

# Campos obrigatórios em todo log estruturado
REQUIRED_LOG_FIELDS = frozenset(
    {
        "asctime",
        "levelname",
        "name",
        "message",
        "correlation_id",
        "service",
    }
)

# Mapeamento de nomes de campos para formato padrão
FIELD_RENAME_MAP = {
    "levelname": "level",
    "name": "logger",
}


def create_json_formatter() -> JsonFormatter:
    """Cria formatter JSON com campos padronizados.

    Returns:
        JsonFormatter configurado para logs estruturados.

    Exemplo de output:
        {
            "asctime": "2026-02-02T10:30:00",
            "level": "INFO",
            "logger": "app.services.foo",
            "message": "Operação concluída",
            "correlation_id": "abc-123",
            "service": "atende_pyloto"
        }
    """
    format_string = " ".join(f"%({field})s" for field in REQUIRED_LOG_FIELDS)

    return JsonFormatter(
        format_string,
        rename_fields=FIELD_RENAME_MAP,
    )
