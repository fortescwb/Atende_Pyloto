# Copilot Instructions — Atende_Pyloto

## Architecture Overview

WhatsApp B2B lead qualification system using **OttoAgent** (single LLM agent) + **FSM** (finite state machine). Core flow: `Webhook → Normalization → Dedupe → Session → OttoAgent → Validation → Outbound`.

### Layer Boundaries (STRICT)

```
src/
├── ai/      # LLM, prompts, models. NO direct IO, cannot import api/
├── api/     # Edge adapters (webhooks, HTTP clients). NO business logic
├── app/     # Orchestration, use cases, infra. The "heart" of the system
├── config/  # Settings, logging config
├── fsm/     # Deterministic state machine (states, transitions, rules)
└── utils/   # Cross-cutting helpers (no business rules)
```

**Import rules:** `api/` calls `app/`, never reverse. `ai/` does no IO—uses protocols. Only `app/bootstrap/` wires concrete implementations.

### Key Components

- **OttoAgent** ([src/ai/services/otto_agent.py](src/ai/services/otto_agent.py)): Main decision agent returning `OttoDecision` (next_state, response_text, confidence)
- **SessionState enum** ([src/fsm/states/session.py](src/fsm/states/session.py)): `INITIAL`, `TRIAGE`, `COLLECTING_INFO`, `GENERATING_RESPONSE` → terminal states
- **Protocols** ([src/app/protocols/](src/app/protocols/)): Define contracts; implementations live in `app/infra/`
- **Bootstrap** ([src/app/bootstrap/](src/app/bootstrap/)): Composition root—only place for concrete wiring

## Code Conventions

### Mandatory Rules (from REGRAS_E_PADROES.md)

- **Files ≤200 lines**, functions ≤50 lines. Exception requires `# EXCECAO REGRA 2.1: <motivo>`
- **Comments in PT-BR** explaining the "why"
- **snake_case** for files/folders
- **Type hints** required on all public interfaces
- **Pydantic models** for structured data (see `OttoDecision`, `OttoRequest` in [src/ai/models/otto.py](src/ai/models/otto.py))

### Logging

Structured logs without PII. Always include: `correlation_id`, `component`, `action`, `result`:

```python
logger.info("operation_name", extra={
    "component": "otto_agent",
    "action": "decide",
    "result": "success",
    "correlation_id": correlation_id,
})
```

### Error Handling

- Fail-fast for permanent errors
- Retry with limits for transient errors
- Fallback to `HANDOFF_HUMAN` when LLM fails

## Development Workflow

### Commands

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run linter (GATE - must pass)
ruff check src/ tests/

# Run tests (GATE - must pass)
pytest -q

# Run with coverage (min 80%)
pytest --cov=src --cov-fail-under=80

# Start server
uvicorn app.app:app --reload --host 0.0.0.0 --port 8080
```

### Testing Strategy

- Test **behavior/contracts**, not every function
- Use fakes/mocks for IO (see [tests/test_e2e/test_golden_path.py](tests/test_e2e/test_golden_path.py))
- Priority: unit (FSM, validators) → integration (use cases) → E2E (minimal, critical paths)
- Mark tests: `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.e2e`

## Key Patterns

### Adding New AI Agent

1. Create model in `src/ai/models/` with Pydantic
2. Create service in `src/ai/services/` (≤200 lines)
3. Define protocol in `src/app/protocols/` if needed
4. Wire in `src/app/bootstrap/`

### Adding New State

1. Add to `SessionState` enum in [src/fsm/states/session.py](src/fsm/states/session.py)
2. Update `TERMINAL_STATES` if terminal
3. Add to `StateName` literal in [src/ai/models/otto.py](src/ai/models/otto.py)
4. Update transition rules in `src/fsm/transitions/`

### Use Case Structure

```python
# src/app/use_cases/whatsapp/example.py
class ExampleUseCase:
    def __init__(self, store: StoreProtocol, agent: AgentProtocol):
        self._store = store
        self._agent = agent
    
    async def execute(self, request: RequestModel) -> ResponseModel:
        # orchestration logic, no direct IO implementation
```

## Critical Integration Points

- **WhatsApp Cloud API**: [src/api/connectors/whatsapp/](src/api/connectors/whatsapp/)
- **OpenAI**: Configured via `OPENAI_API_KEY`, models in settings
- **Firestore**: Session/lead persistence
- **Redis (Upstash)**: Dedupe, rate limiting

## Deployment

Cloud Run via Cloud Build. See [cloudbuild.yaml](cloudbuild.yaml). `ENVIRONMENT` var controls strict validation (`staging`/`production` = fail-fast on missing config).
