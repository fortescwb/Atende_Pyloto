"""Helper para chamadas HTTP à API OpenAI.

Implementação concreta de IO — pertence a app/infra conforme REGRAS § 2.3.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from ai.config.settings import AISettings
    from ai.config.settings import AIModelSettings

logger = logging.getLogger(__name__)

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Alguns modelos (ex.: gpt-5*) não aceitam temperatura customizada.
_TEMPERATURE_LOCKED_PREFIXES = ("gpt-5",)


def _supports_custom_temperature(model_name: str) -> bool:
    """Retorna True se o modelo aceita temperatura customizada."""
    return not model_name.startswith(_TEMPERATURE_LOCKED_PREFIXES)


async def call_openai_api(
    *,
    http_client: httpx.AsyncClient,
    api_key: str,
    settings: AISettings,
    model_settings: AIModelSettings | None = None,
    system_prompt: str,
    user_prompt: str,
    point_name: str,
) -> str | None:
    """Executa chamada à API OpenAI.

    Args:
        http_client: Cliente HTTP async
        api_key: API key da OpenAI
        settings: Configurações de IA
        system_prompt: Prompt de sistema
        user_prompt: Prompt do usuário
        point_name: Nome do ponto LLM (para logs)

    Returns:
        Resposta da API ou None em caso de erro
    """
    if not api_key:
        logger.error("openai_api_key_missing", extra={"point": point_name})
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    model_cfg = model_settings or settings.model

    # GPT-5+ usa max_completion_tokens em vez de max_tokens
    payload = {
        "model": model_cfg.model,
        "max_completion_tokens": model_cfg.max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    # Só envia temperatura quando o modelo suporta customização.
    if _supports_custom_temperature(model_cfg.model) and model_cfg.temperature != 1.0:
        payload["temperature"] = model_cfg.temperature

    try:
        response = await http_client.post(OPENAI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if content:
            logger.debug(
                "openai_call_success",
                extra={
                    "point": point_name,
                    "model": settings.model.model,
                    "tokens_used": data.get("usage", {}).get("total_tokens"),
                },
            )
            return content

        logger.warning("openai_empty_response", extra={"point": point_name})
        return None

    except httpx.TimeoutException:
        logger.warning(
            "openai_timeout",
            extra={"point": point_name, "timeout": settings.timeout.request_timeout},
        )
        return None

    except httpx.HTTPStatusError as e:
        # Extract OpenAI error message when available (safe to log)
        try:
            err_body = e.response.json()
            err_message = err_body.get("error", {}).get("message")
        except Exception:
            err_message = e.response.text

        logger.warning(
            "openai_http_error",
            extra={"point": point_name, "status_code": e.response.status_code, "error": err_message},
        )
        # Also log the raw response body at WARNING level (truncated) so it appears in staging logs
        try:
            body_text = e.response.text
        except Exception:
            body_text = "<unavailable>"
        logger.warning(
            "openai_http_response_text",
            extra={"point": point_name, "response_text": (body_text[:1000] + "..." ) if len(body_text) > 1000 else body_text},
        )
        logger.debug("openai_http_response", extra={"point": point_name, "response_text": body_text})
        return None

    except Exception:
        logger.error("openai_unexpected_error", extra={"point": point_name})
        return None
