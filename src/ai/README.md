# AI Core Module

Este módulo contém toda a lógica central de integração com a OpenAI e gerenciamento de estados para o fluxo de mensagens.

```tree
ai/
├── __init__.py
├── config/
│   ├── __init__.py
│   ├── model_config.py         # Configurações do modelo (temperatura, max_tokens, etc)
│   ├── system_prompts.py       # System instructions e prompts base
│   └── state_prompts.py        # Prompts específicos para cada estado
├── core/
│   ├── __init__.py
│   ├── ai_client.py            # Cliente principal para comunicação com OpenAI
│   ├── state_manager.py        # Gerenciamento de estados e transições
│   ├── response_generator.py   # Geração de respostas com base em contexto
│   └── context_manager.py      # Gerenciamento de contexto de conversa
├── services/
│   ├── __init__.py
│   ├── openai_service.py       # Wrapper específico para OpenAI API
│   └── prompt_service.py       # Serviço para manipulação de prompts
├── prompts/
│   ├── __init__.py
│   ├── base_prompts/           # Prompts base e templates
│   │   ├── system_template.j2
│   │   ├── user_template.j2
│   │   └── response_template.j2
│   ├── state_prompts/          # Prompts por estado
│   │   ├── state_01_prompt.j2
│   │   ├── state_02_prompt.j2
│   │   └── ...
│   └── validation_prompts/     # Prompts para validação de respostas
│       ├── response_validation.j2
│       └── intent_classification.j2
├── models/
│   ├── __init__.py
│   ├── state_model.py          # Modelo de estado e transições
│   ├── response_model.py       # Estrutura de resposta esperada
│   └── context_model.py        # Modelo de contexto de conversa
├── rules/
│   ├── __init__.py
│   ├── transition_rules.py     # Regras de transição entre estados
│   ├── response_rules.py       # Regras de formatação de respostas
│   └── validation_rules.py     # Regras de validação de respostas
├── utils/
    ├── __init__.py
    ├── prompt_utils.py         # Funções auxiliares para prompts
    └── response_utils.py       # Funções auxiliares para respostas
```

## Componentes Principais

### 1. Configurações (`config/`)

- **model_config.py**: Configurações do modelo OpenAI (temperature, max_tokens, etc)
- **system_prompts.py**: System instructions principais
- **state_prompts.py**: Prompts específicos para cada estado

### 2. Lógica Principal (`core/`)

- **ai_client.py**: Cliente principal para comunicação com OpenAI API
- **state_manager.py**: Gerenciamento de estados e transições
- **response_generator.py**: Geração de respostas com contexto
- **context_manager.py**: Gerenciamento de contexto de conversa

### 3. Prompts (`prompts/`)

- Templates Jinja2 para diferentes tipos de prompts
- Estrutura organizada por tipo: base, estado específico, validação

### 4. Regras de Negócio (`rules/`)

- **transition_rules.py**: Regras de transição entre estados
- **response_rules.py**: Regras de formatação de respostas
- **validation_rules.py**: Regras de validação de conteúdo

## Uso

### Inicialização

```python
from ai.core.ai_client import AIClient
from ai.core.state_manager import StateManager

# Inicializar cliente
ai_client = AIClient()
state_manager = StateManager()
```

### Processamento de Mensagem

```python
# Processa mensagem e retorna resposta
response = state_manager.process_message(user_message, current_state, context)
```

## Variáveis de Ambiente

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4-turbo
TEMPERATURE=0.7
MAX_COMPLETION_TOKENS=1000  # preferencial; BACKCOMPAT: MAX_TOKENS accepted
```

## Testes

Executar testes:

```bash
cd ai && python -m pytest tests/
```

## Dependências

- openai>=1.0.0
- jinja2>=3.0.0
- python-dotenv>=0.19.0

## Licença

Pyloto Corp - A Multiservice Company
