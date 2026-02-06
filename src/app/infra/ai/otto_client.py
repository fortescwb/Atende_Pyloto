"""Cliente OpenAI para OttoAgent (structured outputs)."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError

from ai.models.otto import OttoDecision
from ai.utils._json_extractor import extract_json_from_response
from config.settings.ai.openai import OpenAISettings, get_openai_settings

logger = logging.getLogger(__name__)


class OttoClient:
    """Cliente LLM para decisao do OttoAgent."""

    __slots__ = ("_client", "_model", "_timeout_seconds", "_use_json_schema")

    def __init__(
        self,
        *,
        settings: OpenAISettings | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        client: AsyncOpenAI | None = None,
    ) -> None:
        cfg = settings or get_openai_settings()
        self._model = model or cfg.model or "gpt-4o"
        base_timeout = float(timeout_seconds or cfg.timeout_seconds or 12.0)
        self._timeout_seconds = max(10.0, min(base_timeout, 15.0))
        self._use_json_schema = True
        if client is not None:
            self._client = client
        else:
            self._client = AsyncOpenAI(
                api_key=api_key or cfg.api_key,
                timeout=self._timeout_seconds,
            )

    async def decide(self, *, system_prompt: str, user_prompt: str) -> OttoDecision | None:
        """Executa chamada OpenAI e retorna OttoDecision validado."""
        response = await self._call_openai(system_prompt, user_prompt)
        if response is None:
            return None

        content = _extract_content(response)
        if not content:
            logger.warning("otto_client_empty_response")
            return None

        data = _parse_json(content)
        if data is None:
            logger.warning("otto_client_parse_failed")
            return None

        try:
            return OttoDecision.model_validate(data)
        except ValidationError:
            logger.warning("otto_client_schema_invalid")
            return None

    async def _call_openai(self, system_prompt: str, user_prompt: str) -> Any | None:
        if self._use_json_schema:
            response_format = _build_response_format()
            try:
                return await self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format=response_format,
                    temperature=0.2,
                    max_tokens=500,
                )
            except Exception as exc:
                logger.warning(
                    "otto_client_openai_error",
                    extra={
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )
                if getattr(exc, "status_code", None) == 400:
                    self._use_json_schema = False

        try:
            return await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=500,
            )
        except Exception as exc:
            logger.warning(
                "otto_client_openai_fallback_error",
                extra={
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            return None


def _build_response_format() -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "next_state": {"type": "string"},
            "response_text": {"type": "string"},
            "message_type": {"type": "string"},
            "confidence": {"type": "number"},
            "requires_human": {"type": "boolean"},
            "reasoning_debug": {"type": "string"},
        },
        "required": [
            "next_state",
            "response_text",
            "message_type",
            "confidence",
            "requires_human",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "otto_decision",
            "strict": True,
            "schema": schema,
        },
    }


def _extract_content(response: Any) -> str | None:
    try:
        return response.choices[0].message.content if response.choices else None
    except Exception:
        return None


def _parse_json(content: str) -> dict[str, Any] | None:
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    extracted = extract_json_from_response(content)
    if isinstance(extracted, dict):
        return extracted
    return None
