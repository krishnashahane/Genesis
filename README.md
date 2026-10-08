# Genesis

Genesis is a Python runtime for autonomous AI-agent systems. It combines an event bus, task queue, memory, permissions, tools, skills, reflection, specialist agents, and a data-driven execution loop behind one runtime.

The default installation is local and deterministic: a mock LLM, in-memory task/event services, and an in-memory memory store. Optional Redis, ChromaDB, Anthropic, Gemini, and LangGraph integrations are available through the `full` extra.

## Quick start

Requirements: Python 3.11+ and pip.

~~~bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
~~~

Run a goal:

~~~bash
python -m genesis run "Design a token-bucket rate limiter"
~~~

Start the API and web UI:

~~~bash
python -m genesis serve
~~~

Open `http://127.0.0.1:8000/`. API docs are at `/docs`, and the health endpoint is `/api/health`.

## LLM providers

### Mock

The default provider is `mock`, so the core package works without an API key or network access.

### Anthropic

Install the optional provider dependencies:

~~~bash
python -m pip install -e ".[full]"
~~~

Then configure:

~~~bash
export GENESIS_LLM_PROVIDER=anthropic
export GENESIS_ANTHROPIC_API_KEY="..."
export GENESIS_LLM_MODEL=claude-sonnet-5-5
~~~

Claude model IDs are versioned; `claude-sonnet-5-5` is a valid current model ID in Anthropic's model documentation. [Anthropic model IDs](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions)

### Gemini

Genesis uses Google's current `google-genai` Python SDK rather than the legacy `google-generativeai` package. [Google migration guide](https://ai.google.dev/gemini-api/docs/migrate)

Configure:

~~~bash
export GENESIS_LLM_PROVIDER=gemini
export GENESIS_GEMINI_API_KEY="..."
export GENESIS_LLM_MODEL=gemini-3.8-flash
~~~

When a real provider is selected, Genesis fails fast if its API key or SDK is unavailable. It does not silently switch to the mock provider.

## REST API

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

In production, every API endpoint except health requires the `X-Genesis-API-Key` header.

## Production configuration

~~~env
GENESIS_ENV=production
GENESIS_API_HOST=0.0.0.0
GENESIS_API_PORT=8000
GENESIS_API_KEY=replace-with-a-long-random-secret
GENESIS_CORS_ORIGINS=https://your-ui.example
GENESIS_MAX_REQUEST_BYTES=1000000
GENESIS_RATE_LIMIT_PER_MINUTE=30

GENESIS_LLM_PROVIDER=anthropic
GENESIS_ANTHROPIC_API_KEY=...
GENESIS_LLM_MODEL=claude-sonnet-5-5

GENESIS_REDIS_URL=
GENESIS_CHROMA_PATH=./.genesis/chroma
~~~

The default API host is `127.0.0.1` for local safety. Set `GENESIS_API_HOST=0.0.0.0` only when the service is intentionally exposed behind a network boundary or reverse proxy.

CORS is allowlist-based. Production startup fails if `GENESIS_API_KEY` is missing.

## Memory

Genesis keeps short-term working memory in a bounded deque and long-term memory through a pluggable vector store. ChromaDB is optional; the offline fallback uses a stable BLAKE2b-based hashing embedder so results do not change with Python's randomized hash seed.

Reflection stores reusable run lessons, while the execution loop remains data-driven through `Phase` objects.

## Security

- Production API access requires an API key.
- API requests are rate-limited per client.
- Declared request bodies larger than `GENESIS_MAX_REQUEST_BYTES` are rejected.
- Request models enforce practical length/count limits.
- CORS is an explicit allowlist, never wildcard by default.
- Agent system prompts are not returned by the public agent list endpoint.
- Tool execution remains permission-gated.
- The calculator parses an AST and never executes Python `eval`.
- Redis connection strings are never written to logs.
- Generated Python bytecode, virtual environments, build output, and runtime state are ignored by Git.

## Project layout

~~~text
Genesis/
├── genesis/
├── tests/
├── web/
├── ARCHITECTURE.md
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
└── LICENSE
~~~

## Development

~~~bash
pytest
ruff check .
mypy genesis
~~~

## License

MIT
