"""Helper para chamadas HTTP à API OpenAI.

Implementação concreta de IO — pertence a app/infra conforme REGRAS § 2.3.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from ai.config.settings import AISettings

logger = logging.getLogger(__name__)

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


async def call_openai_api(
    *,
    http_client: httpx.AsyncClient,
    api_key: str,
    settings: AISettings,
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

    payload = {
        "model": settings.model.model,
        "temperature": settings.model.temperature,
        "max_tokens": settings.model.max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }

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
        logger.warning(
            "openai_http_error",
            extra={"point": point_name, "status_code": e.response.status_code},
        )
        return None

    except Exception:
        logger.error("openai_unexpected_error", extra={"point": point_name})
        return None
