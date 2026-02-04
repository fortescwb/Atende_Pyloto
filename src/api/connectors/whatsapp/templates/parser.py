"""Parser de resposta da API Meta para templates."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from .models import TemplateCategory, TemplateMetadata, TemplateParameter, TemplateStatus


def extract_parameters(components: list[dict]) -> list[TemplateParameter]:
    """Extrai parâmetros dos componentes do template."""
    params: list[TemplateParameter] = []
    index = 1

    for component in components:
        comp_type = component.get("type", "").upper()

        if comp_type == "BODY":
            text = component.get("text", "")
            matches = re.findall(r"\{\{(\d+)\}\}", text)
            for _ in matches:
                params.append(TemplateParameter(type="text", index=index))
                index += 1

        if comp_type == "HEADER":
            header_format = component.get("format", "TEXT")
            if header_format in ("IMAGE", "VIDEO", "DOCUMENT"):
                params.append(TemplateParameter(type=header_format.lower(), index=index))
                index += 1

    return params


def parse_template_response(data: dict, namespace: str) -> TemplateMetadata:
    """Converte resposta da API em TemplateMetadata."""
    components = data.get("components", [])
    return TemplateMetadata(
        name=data.get("name", ""),
        namespace=namespace,
        language=data.get("language", "pt_BR"),
        category=TemplateCategory(data.get("category", "UTILITY")),
        status=TemplateStatus(data.get("status", "PENDING")),
        components=components,
        parameters=extract_parameters(components),
        last_synced_at=datetime.now(tz=UTC),
    )
