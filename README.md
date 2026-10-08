# Genesis

Genesis is a Python runtime for autonomous AI-agent systems. It combines an event bus, task queue, memory, permissions, tools, skills, reflection, specialist agents, and a data-driven execution loop behind one runtime.

The default configuration runs locally with a deterministic mock LLM and in-memory services. External providers and persistence backends are optional.

## Quick start

Requirements:

- Python 3.11+
- pip

Install the core package:

~~~bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
~~~

Run a goal:

~~~bash
python -m genesis run "Design a token-bucket rate limiter"
~~~

Start the API and web UI:

~~~bash
python -m genesis serve
~~~

Open:

- Web UI: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/health`

Run tests:

~~~bash
python -m pip install -e ".[dev]"
pytest
~~~

## LLM providers

Genesis defaults to `mock`, so the basic install does not require an API key or network access.

### Anthropic

Set:

~~~bash
export GENESIS_LLM_PROVIDER=anthropic
export GENESIS_ANTHROPIC_API_KEY="..."
export GENESIS_LLM_MODEL=claude-opus-4-8
~~~

The current default Anthropic model remains `claude-opus-4-8`, which Anthropic lists as active. citeturn774522search0

### Gemini

The optional Gemini integration uses Google's current `google-genai` Python SDK rather than the legacy `google-generativeai` package. citeturn386523search1

Install the full provider/backend set:

~~~bash
python -m pip install -e ".[full]"
~~~

Then set:

~~~bash
export GENESIS_LLM_PROVIDER=gemini
export GENESIS_GEMINI_API_KEY="..."
export GENESIS_LLM_MODEL=gemini-3.8-flash
~~~

Real providers now fail fast when their API key or SDK is missing. Genesis does not silently substitute mock output when a real provider was explicitly requested.

## REST API

The main endpoints are:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Runtime health |
| POST | `/api/runs` | Execute the configured phase loop |
| POST | `/api/tasks` | Queue a task |
| GET | `/api/tasks` | List tasks |
| GET | `/api/tasks/{id}` | Inspect a task |
| GET | `/api/agents` | List agent roles |
| GET | `/api/tools` | List tool schemas |
| POST | `/api/tools/{name}/invoke` | Invoke an allowed tool |
| POST | `/api/memory` | Store memory |
| POST | `/api/memory/recall` | Recall memory |
| GET | `/api/events` | Read recent events |
| GET | `/api/metrics` | Read in-process metrics |

In production, all API endpoints except health require `X-Genesis-API-Key`.

## Production configuration

Important settings use the `GENESIS_` prefix:

~~~env
GENESIS_ENV=production
GENESIS_API_HOST=0.0.0.0
GENESIS_API_PORT=8000
GENESIS_API_KEY=replace-with-a-long-random-secret
GENESIS_CORS_ORIGINS=https://your-ui.example
GENESIS_MAX_REQUEST_BYTES=1000000

GENESIS_LLM_PROVIDER=anthropic
GENESIS_ANTHROPIC_API_KEY=...
GENESIS_LLM_MODEL=claude-opus-4-8

GENESIS_REDIS_URL=
GENESIS_POSTGRES_DSN=
GENESIS_CHROMA_PATH=./.genesis/chroma
~~~

The default API host is `127.0.0.1` for local safety. Set `GENESIS_API_HOST=0.0.0.0` only when you intentionally expose the service behind a network boundary or reverse proxy.

CORS is disabled unless `GENESIS_CORS_ORIGINS` is configured. Production requests are authenticated with the configured API key.

## Architecture

~~~text
goal
  │
  ▼
ExecutionLoop
  ├─ Phase → Agent → LLM
  ├─ Memory recall/store
  ├─ EventBus
  └─ Reflection
        │
        ▼
   Runtime services
   ├─ TaskQueue
   ├─ ToolRegistry + PermissionManager
   ├─ SkillRegistry
   ├─ KnowledgeGraph
   └─ Observability
~~~

The workflow is data-driven: callers can pass a custom list of `Phase` objects instead of using `DEFAULT_PHASES`.

## Memory

Genesis maintains:

- Short-term working memory in a bounded in-process deque.
- Long-term memory through a pluggable vector store.
- ChromaDB persistence when available.
- A deterministic in-memory hashing embedder when ChromaDB is unavailable.

The offline embedder uses a stable BLAKE2b-derived bucket index, so results do not change merely because Python started with a different hash seed.

## Security

- Production API access requires an API key.
- Request bodies are rejected when their declared size exceeds `GENESIS_MAX_REQUEST_BYTES`.
- API request models enforce field length/count bounds.
- CORS is allowlist-based instead of wildcard-enabled.
- Agent system prompts are no longer returned by the public agents endpoint.
- Tool execution remains permission-gated.
- The calculator tool parses an AST and never calls Python `eval`.
- Generated Python bytecode, virtual environments, build output, and runtime state are ignored by Git.
- The package no longer relies on committed `egg-info` metadata.

## Project layout

~~~text
Genesis/
├── genesis/
│   ├── agents/
│   ├── api/
│   ├── core/
│   ├── knowledge/
│   ├── llm/
│   ├── memory/
│   ├── orchestrator/
│   ├── permissions/
│   ├── skills/
│   └── tools/
├── tests/
├── web/
├── ARCHITECTURE.md
├── README.md
├── pyproject.toml
└── LICENSE
~~~

## Development

Useful commands:

~~~bash
pytest
ruff check .
mypy genesis
~~~

For production deployments, put Genesis behind an HTTPS reverse proxy and configure a strong `GENESIS_API_KEY`.

## License

MIT
