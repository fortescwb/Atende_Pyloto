# TODO — Integração Google Calendar (Agendamentos Reais)

> **Objetivo:** Substituir o fluxo atual (Flow WhatsApp → Firestore estático) por agendamentos reais no Google Calendar, com verificação de disponibilidade e criação/cancelamento de eventos.
>
> **Premissa:** Todas as alterações respeitam as boundaries de camada (`REGRAS_E_PADROES.md`). A integração vive em `app/` — nunca em `ai/`, `fsm/` ou `api/`.

---

## Fase 1 — Fundação (Protocolo, Modelos, Settings)

### 1.1 Criar modelos de domínio para agendamento
- Status: ✅ Concluído
- **Arquivo:** `src/app/domain/appointment.py`
- **O quê:**
  - `TimeSlot(start: datetime, end: datetime, available: bool)`
  - `AppointmentData(date: str, time: str, duration_min: int, attendee_name: str, attendee_email: str, attendee_phone: str, description: str, meeting_mode: Literal["online", "presencial"], vertical: str)`
  - `CalendarEvent(event_id: str, html_link: str, start: datetime, end: datetime, status: str)`
- **Regras:** Pydantic models, tipagem explícita, ≤200 linhas

### 1.2 Criar protocolo `CalendarServiceProtocol`
- Status: ✅ Concluído
- **Arquivo:** `src/app/protocols/calendar_service.py`
- **Métodos do contrato:**
  - `async check_availability(date: str, start_hour: int, end_hour: int) → list[TimeSlot]`
  - `async create_event(appointment: AppointmentData) → CalendarEvent`
  - `async cancel_event(event_id: str) → bool`
  - `async get_event(event_id: str) → CalendarEvent | None`
- **Regras:** `typing.Protocol`, sem implementação, sem IO

### 1.3 Registrar protocolo no `__init__.py`
- Status: ✅ Concluído
- **Arquivo:** `src/app/protocols/__init__.py`
- **O quê:** Adicionar `CalendarServiceProtocol` ao `__all__` e importar de `calendar_service`

### 1.4 Criar settings de Calendar
- Status: ✅ Concluído
- **Arquivo:** `src/config/settings/calendar.py`
- **Campos (Pydantic):**
  - `GOOGLE_CALENDAR_ID: str` — ID do calendário alvo
  - `GOOGLE_SERVICE_ACCOUNT_JSON: str | None` — credencial (Secret Manager ou env)
  - `CALENDAR_TIMEZONE: str = "America/Sao_Paulo"`
  - `CALENDAR_SLOT_DURATION_MIN: int = 30`
  - `CALENDAR_BUFFER_BETWEEN_EVENTS_MIN: int = 15`
  - `CALENDAR_BUSINESS_START_HOUR: int = 9`
  - `CALENDAR_BUSINESS_END_HOUR: int = 17`
  - `CALENDAR_ENABLED: bool = False` — feature flag para rollout gradual
- **Factory:** `get_calendar_settings() → CalendarSettings`

### 1.5 Registrar settings no aggregador
- Status: ✅ Concluído
- **Arquivo:** `src/config/settings/__init__.py`
- **O quê:** Importar e re-exportar `CalendarSettings` e `get_calendar_settings`

---

## Fase 2 — Implementação Concreta (Client Google Calendar)

### 2.1 Criar diretório `src/app/infra/calendar/`
- Status: ✅ Concluído
- **Arquivos:**
  - `__init__.py`
  - `google_calendar_client.py`

### 2.2 Implementar `GoogleCalendarClient`
- Status: ✅ Concluído
- **Arquivo:** `src/app/infra/calendar/google_calendar_client.py`
- **Classe:** `GoogleCalendarClient` que implementa `CalendarServiceProtocol`
- **Dependências externas:** `google-api-python-client`, `google-auth`
- **Responsabilidades:**
  - Autenticação via Service Account (`google.oauth2.service_account.Credentials`)
  - `check_availability()`: usa endpoint `freebusy.query` da Calendar API v3
  - `create_event()`: usa `events.insert` com dados do `AppointmentData`
    - Incluir attendee (email do lead), summary, description, conferenceData (Google Meet se online)
    - Enviar convite por email (parâmetro `sendUpdates="all"`)
  - `cancel_event()`: usa `events.delete` ou `events.patch(status="cancelled")`
  - `get_event()`: usa `events.get` para consultar status
- **Logs:** estruturados, sem PII (não logar email/telefone)
- **Erros:** tratar `HttpError`, retry para 429/5xx, fail-fast para 4xx permanentes
- **Regras:** ≤200 linhas, tipagem explícita, comentários PT-BR

### 2.3 Adicionar dependências ao `pyproject.toml`
- Status: ✅ Concluído
- **Pacotes:**
  - `google-api-python-client>=2.0`
  - `google-auth>=2.0`
  - `google-auth-httplib2>=0.1`

---

## Fase 3 — Bootstrap (Wiring)

### 3.1 Criar factory no bootstrap
- Status: ✅ Concluído
- **Arquivo:** `src/app/bootstrap/dependencies_services.py`
- **Adicionar:** `create_calendar_service() → CalendarServiceProtocol`
  - Lê `CalendarSettings`
  - Se `CALENDAR_ENABLED=False`, retorna implementação no-op (ou None)
  - Se habilitado, instancia `GoogleCalendarClient` com credenciais

### 3.2 Re-exportar na fachada
- Status: ✅ Concluído
- **Arquivo:** `src/app/bootstrap/dependencies.py`
- **O quê:** Importar e incluir `create_calendar_service` no `__all__`

---

## Fase 4 — Serviços Existentes (Adaptar)

### 4.1 Atualizar `appointment_availability.py`
- Status: ✅ Concluído
- **Arquivo:** `src/app/services/appointment_availability.py`
- **Mudanças:**
  - `get_available_dates()` → receber parâmetro opcional `calendar_service: CalendarServiceProtocol | None`
  - Se `calendar_service` fornecido: consultar `check_availability()` por data e filtrar dias sem nenhum slot livre
  - Se `None` (fallback): manter comportamento atual (dias úteis estáticos)
  - `get_available_times()` → idem, filtrar horários ocupados no Google Calendar
- **Compatibilidade:** manter assinatura retrocompatível (parâmetro opcional)

### 4.2 Atualizar `appointment_handler.py`
- Status: ✅ Concluído
- **Arquivo:** `src/app/services/appointment_handler.py`
- **Mudanças em `save_appointment_from_flow()`:**
  - Adicionar parâmetro opcional `calendar_service: CalendarServiceProtocol | None`
  - Após gravar no Firestore (fluxo atual mantido):
    1. Montar `AppointmentData` a partir do `record`
    2. Chamar `calendar_service.create_event(appointment_data)`
    3. Salvar `event_id` e `html_link` retornados no documento Firestore (merge)
  - Tratar erro de calendário **sem impedir** a gravação no Firestore (resiliência)
  - Logar sucesso/falha com `correlation_id`, sem PII

### 4.3 Atualizar `otto_guard_funnel_questions.py`
- Status: ✅ Concluído
- **Arquivo:** `src/app/services/otto_guard_funnel_questions.py`
- **Mudança em `build_next_step_cta()`:**
  - Antes de disparar o template de agendamento, consultar disponibilidade real
  - Se nenhum slot disponível nas próximas 2 semanas: retornar mensagem alternativa ("Nosso time está com a agenda cheia, vamos entrar em contato assim que liberar")
  - Injetar `calendar_service` como parâmetro opcional na função

---

## Fase 5 — Pipeline Inbound (Injeção e Trigger)

### 5.1 Atualizar `ProcessInboundCanonicalUseCase`
- Status: ✅ Concluído
- **Arquivo:** `src/app/use_cases/whatsapp/process_inbound_canonical.py`
- **Mudança:** Adicionar `calendar_service: CalendarServiceProtocol | None = None` no `__init__` e repassar ao `InboundMessageProcessor`

### 5.2 Atualizar `InboundMessageProcessor`
- Status: ✅ Concluído
- **Arquivo:** `src/app/use_cases/whatsapp/_inbound_processor.py`
- **Mudanças:**
  - Receber `calendar_service` no construtor
  - Em `_handle_flow_completion()`: após salvar appointment no Firestore, criar evento no Google Calendar via `calendar_service`
  - Armazenar `event_id` na sessão ou no registro do appointment

### 5.3 Atualizar `_inbound_processor_state_adjustments.py`
- Status: ✅ Concluído
- **Arquivo:** `src/app/use_cases/whatsapp/_inbound_processor_state_adjustments.py`
- **Mudança em `adjust_for_meeting_collected()`:**
  - Quando detectar dados completos (datetime + email) e transitar para `SCHEDULED_FOLLOWUP`, sinalizar que é necessário criar evento
  - Opção: adicionar campo `scheduling_action: str` no `OttoDecision.reasoning_debug` ou usar custom_metadata na sessão

### 5.4 Atualizar factory do WhatsApp
- Status: ✅ Concluído
- **Arquivo:** `src/app/bootstrap/whatsapp_factory.py`
- **O quê:** Injetar `calendar_service` no `ProcessInboundCanonicalUseCase` durante a montagem

---

## Fase 6 — Testes

### 6.1 Fake/Mock do CalendarServiceProtocol
- Status: ✅ Concluído
- **Arquivo:** `tests/fakes/fake_calendar_service.py`
- **O quê:** Implementação in-memory para testes determinísticos
  - `check_availability()` retorna slots pré-definidos
  - `create_event()` retorna `CalendarEvent` fake com `event_id` gerado
  - `cancel_event()` retorna `True`

### 6.2 Testes unitários do client
- Status: ✅ Concluído
- **Arquivos:**
  - `tests/test_app/test_infra/test_calendar/test_google_calendar_client.py`
  - `tests/test_app/test_infra/test_calendar/test_google_calendar_client_errors.py`
- **Cobrir:**
  - Autenticação com credenciais válidas/inválidas
  - Parsing de resposta `freebusy.query`
  - Criação de evento com dados completos/parciais
  - Tratamento de `HttpError` (429, 403, 404, 500)
  - Retry em erros transientes

### 6.3 Testes de integração do appointment_handler
- Status: ✅ Concluído
- **Arquivo:** `tests/app/services/test_appointment_handler.py`
- **Cobrir:**
  - `save_appointment_from_flow()` com `calendar_service` → verifica chamada a `create_event()`
  - `save_appointment_from_flow()` sem `calendar_service` → comportamento retrocompatível
  - Falha no calendar não impede gravação no Firestore

### 6.4 Teste E2E do golden path com agendamento
- Status: ✅ Concluído
- **Arquivo:** `tests/test_e2e/test_scheduling_golden_path.py`
- **Cobrir:**
  - Fluxo completo: lead qualificado → Flow WhatsApp → completion → evento criado no calendar (fake)
  - Transição FSM para `SCHEDULED_FOLLOWUP` correta
  - Dados do evento coerentes com dados do lead

---

## Fase 7 — Configuração de Infra e Deploy

### 7.1 Secrets no GCP Secret Manager
- Criar secret `GOOGLE_SERVICE_ACCOUNT_KEY` com JSON da Service Account
- Criar secret `GOOGLE_CALENDAR_ID`
- Garantir que a Service Account tem role `roles/calendar.writer` no calendário alvo

### 7.2 Variáveis de ambiente no Cloud Run
- Adicionar ao `cloudbuild.yaml` ou configuração do Cloud Run:
  - `GOOGLE_CALENDAR_ID`
  - `GOOGLE_SERVICE_ACCOUNT_JSON` (via Secret Manager mount)
  - `CALENDAR_ENABLED=true` (somente em staging primeiro)

### 7.3 Feature flag para rollout
- Deploy com `CALENDAR_ENABLED=false` em produção
- Testar em staging com calendário de teste
- Ativar em produção após validação
- Nota: Pendente — configuração manual no GCP

---

## Fase 8 — Validação e Gates

### 8.1 Gates obrigatórios (antes de cada PR)
```bash
ruff check src/ tests/
pytest -q
pytest --cov=src --cov-fail-under=80
```

Status da última execução:
- ✅ `ruff check src/ tests/` — passou
- ✅ `pytest -q` — 471 passed
- ❌ `pytest --cov=src --cov-fail-under=80` — 67.65% (<80%)

### 8.2 Checklist de revisão
- [x] Boundaries respeitadas (`app/infra/` faz IO, `app/protocols/` define contrato)
- [x] Nenhum import de `app/infra/calendar/` em `ai/`, `fsm/` ou `api/`
- [x] Arquivos ≤200 linhas, funções ≤50 linhas
- [x] Logs sem PII (sem email, telefone, nome)
- [x] Comentários em PT-BR
- [x] Feature flag funcional (`CALENDAR_ENABLED`)
- [x] Testes determinísticos (sem chamadas reais à API Google)
- [x] Retrocompatibilidade mantida (parâmetros opcionais)

Obs.: `src/app/use_cases/whatsapp/_inbound_processor.py` permanece acima de 200 linhas com exceção já documentada no cabeçalho (`EXCECAO REGRA 2.1`).

---

## Ordem de Execução Recomendada

```
Fase 1 (Fundação)
  └── 1.1 → 1.2 → 1.3 → 1.4 → 1.5
Fase 2 (Client)
  └── 2.3 → 2.1 → 2.2
Fase 3 (Bootstrap)
  └── 3.1 → 3.2
Fase 6.1 (Fake — necessário para testar Fases 4 e 5)
Fase 4 (Serviços) — pode ser paralela
  └── 4.1 | 4.2 | 4.3
Fase 5 (Pipeline)
  └── 5.4 → 5.1 → 5.2 → 5.3
Fase 6 (Testes restantes)
  └── 6.2 → 6.3 → 6.4
Fase 7 (Infra/Deploy)
Fase 8 (Validação)
```

---

## Arquivos Criados vs Atualizados

| Ação | Caminho |
|------|---------|
| **CRIAR** | `src/app/domain/appointment.py` |
| **CRIAR** | `src/app/protocols/calendar_service.py` |
| **CRIAR** | `src/config/settings/calendar.py` |
| **CRIAR** | `src/app/infra/calendar/__init__.py` |
| **CRIAR** | `src/app/infra/calendar/google_calendar_client.py` |
| **CRIAR** | `tests/fakes/fake_calendar_service.py` |
| **CRIAR** | `tests/test_app/test_infra/test_calendar/test_google_calendar_client.py` |
| **CRIAR** | `tests/test_app/test_infra/test_calendar/test_google_calendar_client_errors.py` |
| **CRIAR** | `tests/app/services/test_appointment_handler.py` |
| **CRIAR** | `tests/test_e2e/test_scheduling_golden_path.py` |
| ATUALIZAR | `src/app/protocols/__init__.py` |
| ATUALIZAR | `src/config/settings/__init__.py` |
| ATUALIZAR | `src/app/bootstrap/dependencies_services.py` |
| ATUALIZAR | `src/app/bootstrap/dependencies.py` |
| ATUALIZAR | `src/app/services/appointment_availability.py` |
| ATUALIZAR | `src/app/services/appointment_handler.py` |
| ATUALIZAR | `src/app/services/otto_guard_funnel_questions.py` |
| ATUALIZAR | `src/app/use_cases/whatsapp/process_inbound_canonical.py` |
| ATUALIZAR | `src/app/use_cases/whatsapp/_inbound_processor.py` |
| ATUALIZAR | `src/app/use_cases/whatsapp/_inbound_processor_state_adjustments.py` |
| ATUALIZAR | `src/app/bootstrap/whatsapp_factory.py` |
| ATUALIZAR | `pyproject.toml` |
