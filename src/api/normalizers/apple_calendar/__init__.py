"""Normalizer Apple Calendar (CalDAV) — extração e normalização de eventos.

Responsabilidades:
- Extrair eventos de notificações CalDAV/iCloud
- Normalizar para modelo interno de evento de calendário
- Suportar: criação, atualização, cancelamento de eventos

Nota: Apple Calendar usa CalDAV, não webhooks nativos.
Pode requerer polling ou integração via CalDAV.

TODO: Implementar quando canal Apple Calendar for ativado.
"""

__all__: list[str] = []
