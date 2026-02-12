# Roadmap: Implementação de Endpoint para WhatsApp Flows

## Visão Geral

O endpoint precisa:

1. **Receber requisições criptografadas** da Meta (AES-128-GCM + RSA-OAEP)
2. **Validar assinatura HMAC-SHA256** (app secret)
3. **Descriptografar payload** (chave privada RSA)
4. **Processar lógica de negócio** (validar datas/horários, prefill de dados)
5. **Criptografar resposta** (AES invertido)
6. **Retornar como plaintext Base64**

---

## FASE 1: Setup de Criptografia (Prioridade: CRÍTICA)

### 1.1 Gerar Par de Chaves RSA (2048 bits)

```bash
# Gerar chave privada
openssl genrsa -out flow_private_key.pem 2048

# Extrair chave pública
openssl rsa -in flow_private_key.pem -pubout -out flow_public_key.pem

# Armazenar no Secret Manager (GCP)
gcloud secrets create FLOW_PRIVATE_KEY \
  --data-file=flow_private_key.pem \
  --project=pyloto-prod

# NUNCA comitar as chaves no repositório
echo "*.pem" >> .gitignore
```

### 1.2 Upload da Chave Pública para Meta

```bash
# Via Graph API
curl -X POST "https://graph.facebook.com/v21.0/{WHATSAPP_BUSINESS_ACCOUNT_ID}/whatsapp_business_encryption" \
  -H "Authorization: Bearer {WHATSAPP_ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "business_public_key": "'"$(cat flow_public_key.pem)"'"
  }'

# Resposta esperada:
# {"success": true}
```

**Documentação**: A Meta **assina automaticamente** a chave pública após upload. Você só precisa fazer upload uma vez por WABA.

---

## FASE 2: Estrutura de Código (Python/Flask)

### 2.1 Criar módulo de criptografia (Sugestão de código)

**Criar**: `src/app/infra/crypto/flow_encryption.py`

```python
"""Criptografia para WhatsApp Flows (AES-128-GCM + RSA-OAEP)."""

from __future__ import annotations

import base64
import json
from typing import NamedTuple

from cryptography.hazmat.primitives.asymmetric.padding import OAEP, MGF1, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_pem_private_key


class DecryptedRequest(NamedTuple):
    """Payload descriptografado + materiais de criptografia."""
    payload: dict
    aes_key: bytes
    iv: bytes


def decrypt_flow_request(
    encrypted_flow_data_b64: str,
    encrypted_aes_key_b64: str,
    initial_vector_b64: str,
    private_key_pem: str,
) -> DecryptedRequest:
    """Descriptografa requisição do WhatsApp Flow.

    Args:
        encrypted_flow_data_b64: Payload criptografado (base64)
        encrypted_aes_key_b64: Chave AES criptografada com RSA (base64)
        initial_vector_b64: IV (base64)
        private_key_pem: Chave privada RSA (PEM string)

    Returns:
        DecryptedRequest com payload JSON + materiais para resposta

    Raises:
        ValueError: Se decriptografia falhar
    """
    # 1. Decodificar Base64
    flow_data = base64.b64decode(encrypted_flow_data_b64)
    iv = base64.b64decode(initial_vector_b64)
    encrypted_aes_key = base64.b64decode(encrypted_aes_key_b64)

    # 2. Descriptografar chave AES usando RSA-OAEP
    private_key = load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
    )
    aes_key = private_key.decrypt(
        encrypted_aes_key,
        OAEP(
            mgf=MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    # 3. Descriptografar payload usando AES-128-GCM
    encrypted_body = flow_data[:-16]  # Dados sem tag
    auth_tag = flow_data[-16:]  # Authentication tag (últimos 16 bytes)

    cipher = Cipher(
        algorithms.AES(aes_key),
        modes.GCM(iv, auth_tag),
    )
    decryptor = cipher.decryptor()
    decrypted_bytes = decryptor.update(encrypted_body) + decryptor.finalize()

    # 4. Parsear JSON
    payload = json.loads(decrypted_bytes.decode("utf-8"))

    return DecryptedRequest(payload, aes_key, iv)


def encrypt_flow_response(
    response: dict,
    aes_key: bytes,
    iv: bytes,
) -> str:
    """Criptografa resposta para WhatsApp Flow.

    Args:
        response: Payload JSON a ser criptografado
        aes_key: Chave AES recebida no request
        iv: IV recebido no request

    Returns:
        String Base64 criptografada
    """
    # 1. Inverter IV (XOR com 0xFF)
    flipped_iv = bytes(byte ^ 0xFF for byte in iv)

    # 2. Criptografar com AES-128-GCM
    cipher = Cipher(
        algorithms.AES(aes_key),
        modes.GCM(flipped_iv),
    )
    encryptor = cipher.encryptor()
    response_bytes = json.dumps(response).encode("utf-8")

    ciphertext = encryptor.update(response_bytes) + encryptor.finalize()

    # 3. Concatenar ciphertext + auth tag
    encrypted_data = ciphertext + encryptor.tag

    # 4. Retornar como Base64
    return base64.b64encode(encrypted_data).decode("utf-8")
```

---

### 2.2 Criar Blueprint de Endpoint (Sugestão de código)

**Criar**: `src/api/routes/whatsapp_flow_endpoint.py`

```python
"""Endpoint para WhatsApp Flows (data_exchange + health check)."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from flask import Blueprint, Response, jsonify, request

from app.infra.crypto.flow_encryption import (
    DecryptedRequest,
    decrypt_flow_request,
    encrypt_flow_response,
)
from config.settings.whatsapp.api import WHATSAPP_APP_SECRET, FLOW_PRIVATE_KEY

logger = logging.getLogger(__name__)

flow_bp = Blueprint("flow_endpoint", __name__)


def _verify_signature(body_bytes: bytes, signature_header: str) -> bool:
    """Valida assinatura HMAC-SHA256 da Meta.

    Args:
        body_bytes: Corpo da requisição (raw bytes)
        signature_header: Header X-Hub-Signature-256 (formato: sha256=HASH)

    Returns:
        True se assinatura válida
    """
    if not signature_header.startswith("sha256="):
        return False

    received_signature = signature_header[7:]  # Remove "sha256="

    expected_signature = hmac.new(
        WHATSAPP_APP_SECRET.encode(),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, received_signature)


@flow_bp.post("/whatsapp/flow/endpoint")
def handle_flow_request() -> Response:
    """Endpoint unificado para WhatsApp Flow requests.

    Trata:
    - Health check (ping)
    - Data exchange (INIT, data_exchange, BACK)
    - Error notifications
    """
    # 1. Validar assinatura
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not _verify_signature(request.data, signature):
        logger.warning(
            "flow_signature_invalid",
            extra={
                "component": "flow_endpoint",
                "action": "signature_validation",
                "result": "failed",
            },
        )
        return Response("Signature verification failed", status=401)

    # 2. Parsear JSON criptografado
    try:
        body = request.json
        encrypted_flow_data = body["encrypted_flow_data"]
        encrypted_aes_key = body["encrypted_aes_key"]
        initial_vector = body["initial_vector"]
    except (KeyError, TypeError) as exc:
        logger.error(
            "flow_malformed_request",
            extra={
                "component": "flow_endpoint",
                "error": str(exc),
            },
        )
        return Response("Malformed request", status=400)

    # 3. Descriptografar
    try:
        decrypted = decrypt_flow_request(
            encrypted_flow_data,
            encrypted_aes_key,
            initial_vector,
            FLOW_PRIVATE_KEY,
        )
    except Exception as exc:
        logger.error(
            "flow_decryption_failed",
            extra={
                "component": "flow_endpoint",
                "error": str(exc),
            },
        )
        # HTTP 421: força cliente a re-baixar public key
        return Response("Decryption failed", status=421)

    # 4. Rotear por action
    action = decrypted.payload.get("action")

    if action == "ping":
        return _handle_health_check(decrypted)

    if action in ("INIT", "data_exchange", "BACK"):
        return _handle_data_exchange(decrypted)

    # Unknown action
    logger.warning(
        "flow_unknown_action",
        extra={
            "component": "flow_endpoint",
            "action": action,
        },
    )
    return Response("Unknown action", status=400)


def _handle_health_check(decrypted: DecryptedRequest) -> Response:
    """Health check: ping → pong."""
    response_payload = {"data": {"status": "active"}}

    encrypted_response = encrypt_flow_response(
        response_payload,
        decrypted.aes_key,
        decrypted.iv,
    )

    logger.info(
        "flow_health_check",
        extra={
            "component": "flow_endpoint",
            "action": "ping",
            "result": "success",
        },
    )

    return Response(encrypted_response, mimetype="text/plain")


def _handle_data_exchange(decrypted: DecryptedRequest) -> Response:
    """Processa data_exchange (lógica de negócio)."""
    payload = decrypted.payload
    action = payload["action"]
    screen = payload.get("screen")
    data = payload.get("data", {})
    flow_token = payload.get("flow_token")

    logger.info(
        "flow_data_exchange",
        extra={
            "component": "flow_endpoint",
            "action": action,
            "screen": screen,
            "flow_token": flow_token,
        },
    )

    # LÓGICA DE NEGÓCIO (implementar Fase 3)
    response_payload = _process_flow_logic(
        action=action,
        screen=screen,
        data=data,
        flow_token=flow_token,
    )

    encrypted_response = encrypt_flow_response(
        response_payload,
        decrypted.aes_key,
        decrypted.iv,
    )

    return Response(encrypted_response, mimetype="text/plain")


def _process_flow_logic(
    action: str,
    screen: str | None,
    data: dict[str, Any],
    flow_token: str | None,
) -> dict[str, Any]:
    """Lógica de negócio do Flow (PLACEHOLDER - implementar Fase 3).

    Args:
        action: INIT | data_exchange | BACK
        screen: Nome da tela atual
        data: Dados submetidos pelo usuário
        flow_token: Token para identificar sessão (wa_id)

    Returns:
        Payload de resposta (next screen ou SUCCESS)
    """
    # FASE 3: Implementar lógica real
    # - INIT: retornar APPOINTMENT com datas disponíveis
    # - vertical_selected: retornar datas disponíveis
    # - date_selected: retornar horários disponíveis
    # - DETAILS submit: validar e navegar para SUMMARY
    # - SUMMARY confirm: retornar SUCCESS

    # MOCK: sempre avança para próxima tela
    if screen == "APPOINTMENT":
        return {
            "screen": "DETAILS",
            "data": {
                "vertical": data.get("vertical"),
                "date": data.get("date"),
                "time": data.get("time"),
            },
        }

    if screen == "DETAILS":
        return {
            "screen": "SUMMARY",
            "data": {
                "summary_text": f"Agendamento: {data.get('date')} às {data.get('time')}",
                "details_text": f"Nome: {data.get('name')}\nEmail: {data.get('email')}",
                "vertical": data.get("vertical"),
                "date": data.get("date"),
                "time": data.get("time"),
                "name": data.get("name"),
                "email": data.get("email"),
                "phone": data.get("phone"),
                "company": data.get("company", ""),
                "need_description": data.get("need_description", ""),
            },
        }

    if screen == "SUMMARY":
        # Flow completion
        return {
            "screen": "SUCCESS",
            "data": {
                "extension_message_response": {
                    "params": {
                        "flow_token": flow_token,
                        "vertical": data.get("vertical"),
                        "date": data.get("date"),
                        "time": data.get("time"),
                        "name": data.get("name"),
                        "email": data.get("email"),
                    },
                },
            },
        }

    # Fallback
    return {
        "screen": "APPOINTMENT",
        "data": {},
    }
```

---

### 2.3 Adicionar Settings (Sugestão de código)

**Editar**: `src/config/settings/whatsapp/api.py`

```python
# Adicionar ao final do arquivo
import os

# Flow Endpoint
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET")  # App secret da Meta
FLOW_PRIVATE_KEY = os.getenv("FLOW_PRIVATE_KEY")  # Chave privada RSA (PEM)

if not WHATSAPP_APP_SECRET:
    raise ValueError("WHATSAPP_APP_SECRET must be set")

if not FLOW_PRIVATE_KEY:
    raise ValueError("FLOW_PRIVATE_KEY must be set")
```

---

### 2.4 Registrar Blueprint (Sugestão de código)

**Editar**: `src/api/__init__.py` (ou onde blueprints são registrados)

```python
from api.routes.whatsapp_flow_endpoint import flow_bp

def create_app():
    app = Flask(__name__)

    # ... blueprints existentes

    app.register_blueprint(flow_bp)  # ADICIONAR

    return app
```

---

## FASE 3: Lógica de Negócio (Agendamento)

### 3.1 Criar serviço de disponibilidade (Sugestão de código)

**Criar**: `src/app/services/appointment_availability.py`

```python
"""Serviço para calcular datas/horários disponíveis para agendamento."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import NamedTuple


class AvailableSlot(NamedTuple):
    """Slot de horário disponível."""
    id: str  # "2026-02-10"
    title: str  # "Ter, 10 de Fev"
    enabled: bool = True


def get_available_dates(vertical: str, days_ahead: int = 14) -> list[dict]:
    """Retorna próximas datas disponíveis (exceto fins de semana).

    Args:
        vertical: ID da vertente (sob_medida, automacao, etc)
        days_ahead: Quantos dias para frente buscar

    Returns:
        Lista de datas no formato Flow JSON
    """
    available = []
    today = datetime.now()

    for i in range(1, days_ahead + 1):
        date = today + timedelta(days=i)

        # Skip weekends (sábado=5, domingo=6)
        if date.weekday() in (5, 6):
            continue

        available.append({
            "id": date.strftime("%Y-%m-%d"),
            "title": date.strftime("%a, %d de %b").replace("Mon", "Seg")
                .replace("Tue", "Ter").replace("Wed", "Qua")
                .replace("Thu", "Qui").replace("Fri", "Sex"),
        })

    return available


def get_available_times(date_str: str) -> list[dict]:
    """Retorna horários disponíveis para uma data.

    Args:
        date_str: Data no formato "YYYY-MM-DD"

    Returns:
        Lista de horários no formato Flow JSON
    """
    # Horário comercial: 09:00 - 17:00 (intervalos de 1h)
    times = []
    for hour in range(9, 17):
        times.append({
            "id": f"{hour:02d}:00",
            "title": f"{hour:02d}:00",
            "enabled": True,  # TODO: Integrar com calendário real
        })

    return times
```

---

### 3.2 Refatorar `_process_flow_logic` (real) (Sugestão de código)

**Editar**: `src/api/routes/whatsapp_flow_endpoint.py`

```python
from app.services.appointment_availability import (
    get_available_dates,
    get_available_times,
)

def _process_flow_logic(
    action: str,
    screen: str | None,
    data: dict[str, Any],
    flow_token: str | None,
) -> dict[str, Any]:
    """Lógica de negócio do Flow."""

    # 1. INIT: Primeira tela (APPOINTMENT)
    if action == "INIT":
        return {
            "screen": "APPOINTMENT",
            "data": {
                "vertical": [
                    {"id": "saas", "title": "SaaS Pyloto (Entregas)"},
                    {"id": "sob_medida", "title": "Desenvolvimento Sob Medida"},
                    {"id": "gestao_perfis_trafego", "title": "Gestão de Perfis e Tráfego"},
                    {"id": "automacao_atendimento", "title": "Automação de Atendimento"},
                    {"id": "intermediacao_entregas", "title": "Intermediação de Entregas"},
                ],
                "date": [],  # Vazio até selecionar vertical
                "is_date_enabled": False,
                "time": [],
                "is_time_enabled": False,
            },
        }

    # 2. Trigger: vertical_selected
    trigger = data.get("trigger")
    if trigger == "vertical_selected":
        vertical = data.get("vertical")
        dates = get_available_dates(vertical)

        return {
            "data": {
                "date": dates,
                "is_date_enabled": len(dates) > 0,
            },
        }

    # 3. Trigger: date_selected
    if trigger == "date_selected":
        date = data.get("date")
        times = get_available_times(date)

        return {
            "data": {
                "time": times,
                "is_time_enabled": len(times) > 0,
            },
        }

    # 4. Navigate APPOINTMENT → DETAILS
    if screen == "APPOINTMENT":
        # TODO: Prefill com dados do LeadContact (flow_token = wa_id)
        return {
            "screen": "DETAILS",
            "data": {
                "vertical": data.get("vertical"),
                "date": data.get("date"),
                "time": data.get("time"),
            },
        }

    # 5. DETAILS → SUMMARY
    if screen == "DETAILS":
        return {
            "screen": "SUMMARY",
            "data": {
                "summary_text": f"{_get_vertical_title(data.get('vertical'))}\n{data.get('date')} às {data.get('time')}",
                "details_text": _format_user_details(data),
                **data,  # Passar todos os dados coletados
            },
        }

    # 6. SUMMARY → SUCCESS (flow completion)
    if screen == "SUMMARY":
        return {
            "screen": "SUCCESS",
            "data": {
                "extension_message_response": {
                    "params": {
                        "flow_token": flow_token,
                        **data,  # Todos os dados do agendamento
                    },
                },
            },
        }

    # Fallback
    return {"screen": "APPOINTMENT", "data": {}}


def _get_vertical_title(vertical_id: str) -> str:
    """Mapeia ID para título legível."""
    titles = {
        "saas": "SaaS Pyloto (Entregas)",
        "sob_medida": "Desenvolvimento Sob Medida",
        "gestao_perfis_trafego": "Gestão de Perfis e Tráfego",
        "automacao_atendimento": "Automação de Atendimento",
        "intermediacao_entregas": "Intermediação de Entregas",
    }
    return titles.get(vertical_id, vertical_id)


def _format_user_details(data: dict) -> str:
    """Formata dados do usuário para exibição."""
    lines = [
        f"Nome: {data.get('name', 'N/A')}",
        f"Email: {data.get('email', 'N/A')}",
        f"Telefone: {data.get('phone', 'N/A')}",
    ]

    if data.get("company"):
        lines.append(f"Empresa: {data['company']}")

    if data.get("need_description"):
        lines.append(f"\nNecessidade: {data['need_description']}")

    return "\n".join(lines)
```

---

## FASE 4: Webhook de Completion (Receber Dados)

### 4.1 Atualizar webhook inbound (Sugestão de código)

**Editar**: `src/api/connectors/whatsapp/webhook/inbound.py`

```python
# Adicionar handler para flow completion

def _handle_interactive_message(message: dict) -> NormalizedMessage | None:
    """Processa mensagens interativas (buttons, lists, FLOWS)."""
    interactive = message.get("interactive", {})
    interactive_type = interactive.get("type")

    # ... código existente para buttons/lists ...

    # NOVO: Flow completion
    if interactive_type == "nfm_reply":  # Native Flow Message Reply
        flow_reply = interactive.get("nfm_reply", {})
        response_json = flow_reply.get("response_json")

        if response_json:
            import json
            flow_data = json.loads(response_json)

            # Logar completion
            logger.info(
                "flow_completed",
                extra={
                    "component": "webhook_inbound",
                    "flow_token": flow_data.get("flow_token"),
                    "data": flow_data,
                },
            )

            # Processar agendamento
            from app.services.appointment_handler import save_appointment
            save_appointment(flow_data)

            return NormalizedMessage(
                message_id=message["id"],
                from_number=message["from"],
                timestamp=message["timestamp"],
                message_type="flow_completion",
                text=f"Agendamento confirmado: {flow_data.get('date')} às {flow_data.get('time')}",
            )

    return None
```

---

### 4.2 Criar serviço de salvamento (Sugestão de código)

**Criar**: `src/app/services/appointment_handler.py`

```python
"""Handler para agendamentos via Flow."""

from __future__ import annotations

import logging
from datetime import datetime

from app.protocols.repositories import FirestoreRepository

logger = logging.getLogger(__name__)


async def save_appointment(flow_data: dict) -> None:
    """Salva agendamento no Firestore.

    Args:
        flow_data: Dados do flow completion
    """
    wa_id = flow_data.get("flow_token")  # wa_id é passado como flow_token

    appointment = {
        "wa_id": wa_id,
        "vertical": flow_data.get("vertical"),
        "date": flow_data.get("date"),
        "time": flow_data.get("time"),
        "name": flow_data.get("name"),
        "email": flow_data.get("email"),
        "phone": flow_data.get("phone"),
        "company": flow_data.get("company"),
        "need_description": flow_data.get("need_description"),
        "status": "confirmed",
        "created_at": datetime.utcnow().isoformat(),
    }

    # Salvar no Firestore
    repo = FirestoreRepository()  # Injetar via DI no código real
    await repo.save(f"appointments/{wa_id}_{appointment['date']}_{appointment['time']}", appointment)

    logger.info(
        "appointment_saved",
        extra={
            "component": "appointment_handler",
            "wa_id": wa_id,
            "date": appointment["date"],
            "time": appointment["time"],
        },
    )

    # TODO: Notificar equipe humana
    # await notify_team(appointment)
```

---

## FASE 5: Deploy e Configuração

### 5.1 Atualizar variáveis de ambiente (Sugestão de código)

**Editar**: `.env.example` (e configurar no GCP Secret Manager)

```bash
# WhatsApp Flow Endpoint
WHATSAPP_APP_SECRET=your_app_secret_here
FLOW_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----"
```

### 5.2 Atualizar `cloudbuild.yaml` (Sugestão de código)

```yaml
# Adicionar secrets ao Cloud Run
substitutions:
  _WHATSAPP_APP_SECRET: ${WHATSAPP_APP_SECRET}
  _FLOW_PRIVATE_KEY: ${FLOW_PRIVATE_KEY}
```

### 5.4 Configurar Flow na Meta (Sugestão de código)

```bash
# Upload Flow JSON (com endpoint configurado)
curl -X POST "https://graph.facebook.com/v21.0/{WHATSAPP_BUSINESS_ACCOUNT_ID}/flows" \
  -H "Authorization: Bearer {ACCESS_TOKEN}" \
  -F "name=Agendamento Consultoria Pyloto" \
  -F "categories=[\"APPOINTMENT\"]" \
  -F "endpoint_uri=${SERVICE_URL}/whatsapp/flow/endpoint" \
  -F "flow_json=@docs/whatsapp_flows/appointment_flow.json"

# Resposta: {"id": "FLOW_ID"}

# Publicar Flow
curl -X POST "https://graph.facebook.com/v21.0/{FLOW_ID}/publish" \
  -H "Authorization: Bearer {ACCESS_TOKEN}"
```

---

## FASE 6: Testes e Validação (Sugestão de código)

### 6.1 Testes unitários

**Criar**: `tests/unit/app/infra/crypto/test_flow_encryption.py`

```python
import pytest

from app.infra.crypto.flow_encryption import (
    decrypt_flow_request,
    encrypt_flow_response,
)


def test_decrypt_and_encrypt_roundtrip(mock_private_key):
    """Test decryption + encryption roundtrip."""
    # Mock encrypted request from Meta
    encrypted_request = {
        "encrypted_flow_data": "...",
        "encrypted_aes_key": "...",
        "initial_vector": "...",
    }

    # Decrypt
    decrypted = decrypt_flow_request(
        encrypted_request["encrypted_flow_data"],
        encrypted_request["encrypted_aes_key"],
        encrypted_request["initial_vector"],
        mock_private_key,
    )

    assert decrypted.payload["action"] == "ping"

    # Encrypt response
    response = {"data": {"status": "active"}}
    encrypted_response = encrypt_flow_response(
        response,
        decrypted.aes_key,
        decrypted.iv,
    )

    assert isinstance(encrypted_response, str)
    assert len(encrypted_response) > 0
```

### 6.2 Testar endpoint local

```bash
# Instalar dependências
pip install cryptography flask

# Rodar servidor local
FLASK_APP=src/api flask run --port=3000

# Testar health check (simular encrypted request)
python tests/scripts/test_flow_endpoint_local.py
```

---

## Checklist Final

```checklist
FASE 1: Setup Criptografia
- [ ] Gerar par de chaves RSA 2048 bits
- [ ] Armazenar private key no Secret Manager
- [ ] Upload public key para Meta via API
- [ ] Validar upload (receber success: true)

FASE 2: Código Base
- [ ] Criar flow_encryption.py (decrypt/encrypt)
- [ ] Criar whatsapp_flow_endpoint.py (blueprint)
- [ ] Adicionar settings (APP_SECRET, PRIVATE_KEY)
- [ ] Registrar blueprint no Flask app

FASE 3: Lógica de Negócio
- [ ] Criar appointment_availability.py
- [ ] Implementar get_available_dates()
- [ ] Implementar get_available_times()
- [ ] Refatorar _process_flow_logic() com casos reais

FASE 4: Webhook Completion
- [ ] Atualizar webhook inbound (handle nfm_reply)
- [ ] Criar appointment_handler.py
- [ ] Salvar agendamento no Firestore
- [ ] Notificar equipe humana (email/Slack)

FASE 5: Deploy
- [ ] Configurar env vars (APP_SECRET, PRIVATE_KEY)
- [ ] Deploy staging
- [ ] Upload Flow JSON com endpoint_uri
- [ ] Publicar Flow

FASE 6: Testes
- [ ] Testes unitários (crypto)
- [ ] Teste E2E (enviar Flow → preencher → validar Firestore)
- [ ] Monitorar logs (Cloud Logging)
- [ ] Validar latência (<2s P95)
```

---

## Recursos Críticos

- [Documentação oficial Meta - Implementing Endpoint](https://developers.facebook.com/docs/whatsapp/flows/guides/implementingyourflowendpoint/)
- [WhatsApp Flows Tools (GitHub)](https://github.com/WhatsApp/WhatsApp-Flows-Tools)
- [Exemplo Node.js no Glitch](https://glitch.com/~whatsapp-flows-endpoint-example)
- [Code Examples (Python/Node/PHP/Java)](https://developers.facebook.com/docs/whatsapp/flows/guides/implementingyourflowendpoint/#code-examples)

O roadmap está completo. Priorize **FASE 1** (criptografia) primeiro, pois sem chaves configuradas nada funciona. Depois implemente FASE 2-3 juntas (código + lógica). FASE 4 pode ser paralela. FASE 5-6 são deploy e validação final.
