"""API — camada de borda e adapters de canais.

Responsabilidades:
- Receber requests de canais externos (webhooks)
- Validar assinaturas e payloads
- Normalizar dados para modelos internos
- Construir payloads para APIs externas
- Aplicar validações e limites de API

Subpastas:
- connectors/: adapters HTTP por canal
- normalizers/: conversão de payloads externos → modelos internos
- payload_builders/: construção de payloads para APIs externas
- validators/: validação de payloads e limites
- routes/: endpoints HTTP por canal (webhooks, health, admin)

NÃO PODE conter: FSM, regras de sessão, policies, orquestração de use cases.
"""
