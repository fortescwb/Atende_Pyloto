"""Builder para mensagens de template."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from api.connectors.whatsapp.models import OutboundMessageRequest


class TemplatePayloadBuilder:
    """Builder para mensagens de template."""

    def build(self, request: OutboundMessageRequest) -> dict[str, Any]:
        """Constrói payload para mensagem de template.

        Args:
            request: Requisição com dados de template

        Returns:
            Payload template conforme API Meta
        """
        template_obj: dict[str, Any] = {
            "name": request.template_name,
            "language": {"code": request.language or "pt_BR"},
        }

        components: list[dict[str, Any]] = []

        # Adiciona componente de body se houver parâmetros
        if request.template_params:
            components.append({
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(p)} for p in request.template_params.values()
                ],
            })

        # Adiciona componente de botão com flow se flow_id presente
        if request.flow_id:
            components.append({
                "type": "button",
                "sub_type": "flow",
                "index": "0",
                "parameters": [
                    {
                        "type": "action",
                        "action": {
                            "flow_token": request.flow_token or "unused",
                            "flow_action_data": {},
                        },
                    }
                ],
            })

        if components:
            template_obj["components"] = components

        return {"template": template_obj}
