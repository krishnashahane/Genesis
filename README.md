# 🌌 Genesis

**An open-source runtime and memory operating system for autonomous AI agents.**

Genesis is a kernel for multi-agent systems. It gives a roster of specialist
agents a shared brain (memory), a shared nervous system (an event bus), and a
data-driven execution loop that takes a goal from **Observe → Plan → Research →
Build → Review → Test → Debug → Optimize → Reflect → Store Memory** — then
repeats, getting smarter each time through persistent reflection.

It runs **with zero external services** out of the box (in-memory fallbacks for
every backend) and scales up to Redis + PostgreSQL + ChromaDB for production.

---

## Quickstart

```bash
# 1. Install (core only — no heavy infra needed)
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Run one full execution loop from the CLI
python -m genesis run "Design a token-bucket rate limiter for the REST API"

# 3. Or start the REST API + Web UI
python -m genesis serve          # → http://localhost:8000  (UI)  /docs (API)

# 4. Run the tests
pytest
```

No API keys required: Genesis defaults to a deterministic **mock LLM** so the
entire pipeline runs offline. Add a real provider when you want real reasoning:

```bash
export GENESIS_LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-...
export GENESIS_LLM_MODEL=claude-opus-4-8
pip install -e ".[full]"         # installs anthropic, chromadb, redis, …
```

### Docker

```bash
docker compose up --build        # Genesis + Redis + PostgreSQL
```

---

## Tech stack

| Layer | Technology | Role |
|-------|-----------|------|
| Language | **Python 3.11+** | Async-first core |
| API | **FastAPI + Uvicorn** | REST API & Web UI host |
| Orchestration | **Async execution loop** (+ optional **LangGraph**) | Data-driven phase graph |
| Long-term memory | **ChromaDB** (vector) → in-memory fallback | Persistent semantic recall |
| State / queues | **Redis** → in-memory fallback | Event mirror & task queue |
| Relational | **PostgreSQL** (via SQLAlchemy/asyncpg) | Durable records (optional) |
| LLM | **Anthropic Claude** / **Google Gemini** / **mock** | Pluggable reasoning |
| Validation | **Pydantic v2** | Typed models & settings |
| Observability | **structlog** + in-process metrics | Structured logs (stderr) + `/metrics` |
| Packaging | **Docker / docker-compose** | Self-hosted deployment |
| Tests / quality | **pytest, ruff, mypy** | 38 tests, 90%+ coverage |

Every heavy dependency is **optional**. The core (`pip install -e .`) pulls only
FastAPI, Pydantic, structlog, httpx, tenacity — and degrades gracefully when an
infra backend or provider SDK is absent.

---

## How it works

```
              ┌──────────────────── Runtime (kernel) ────────────────────┐
   goal ──▶   │  EventBus · TaskQueue · MemoryEngine · ToolRegistry ·     │
              │  SkillRegistry · KnowledgeGraph · PermissionManager ·     │
              │  ReflectionEngine · Observability · LLM provider          │
              └───────────────────────────┬──────────────────────────────┘
                                          │  builds & injects into
                                          ▼
   ExecutionLoop  ── data-driven phase list (no hardcoded branching) ──▶ Agents
   observe → plan → research → design → build → review → test → debug → optimize → document
        each phase: recall memory → run agent → emit events → persist episodic memory
                                          │
                                          ▼
                    Reflect → store a durable lesson → recalled on the next run
```

1. **A goal enters** via the CLI, REST API (`POST /api/runs`), or task queue.
2. The **Execution Loop** walks a *list of phases* (`DEFAULT_PHASES`). There is no
   `if phase == "plan"` logic anywhere — reorder/add/remove phases (or pass your
   own list) to change the workflow. This satisfies the **no-hardcoded-workflows**
   requirement.
3. Each phase maps to a **specialist Agent** (CEO, Planner, Research, Architect,
   Coder, Reviewer, Tester, Debugger, Optimizer, Reflection, Documentation). Every
   agent shares the same kernel services and only declares its *identity* (role +
   system prompt), so agents stay uniform and testable.
4. Before acting, an agent **recalls relevant long-term memories** and threads the
   previous phase's output forward via a shared blackboard.
5. Every action is an **event** on the bus (`agent.started`, `tool.invoked`,
   `memory.stored`, …). The Observability layer and Web UI live-feed subscribe to
   `*`, giving a full audit trail. Agents talk to each other with `agent.message`
   events — never direct calls.
6. After the loop, the **Reflection Engine** distils a lesson, stores it as a
   `reflection` memory, and emits `reflection.created`. On the next run, agents
   recall that lesson — closing the **self-improvement loop**.

### Core components

- **Memory Engine** — short-term ring buffer (working memory) + long-term vector
  store (persistent, semantic, survives restarts).
- **Reflection Engine** — turns outcomes into reusable lessons.
- **Runtime** — the kernel; wires and owns every subsystem (DI-friendly).
- **Event Bus** — async pub/sub; topic + wildcard subscriptions; optional Redis mirror.
- **Task Queue** — priority async queue, emits lifecycle events.
- **Tool Registry** — permission-gated, audited tool execution; MCP/LLM-compatible schemas.
- **Skill System** — composable, growable procedures above raw tools.
- **Knowledge Graph** — entity/relationship triples agents learn.
- **Permission System** — capability-based access control with wildcards.
- **Observability Layer** — structured logs + metrics + event history.

---

## REST API

| Method & path | Purpose |
|---|---|
| `GET /api/health` | Runtime & subsystem status |
| `POST /api/runs` | Run the full loop for a goal |
| `POST /api/tasks` · `GET /api/tasks/{id}` | Queue & inspect tasks |
| `GET /api/agents` · `GET /api/tools` | Introspect the roster & capabilities |
| `POST /api/tools/{name}/invoke` | Invoke a tool directly |
| `POST /api/memory` · `POST /api/memory/recall` | Store & semantically recall memory |
| `GET /api/events` · `GET /api/metrics` | Observability feed & metrics |

Interactive docs at `/docs` (Swagger) when the server is running.

---

## Project layout

```
genesis/
  config.py            # typed settings (env-driven, safe defaults)
  observability.py     # structured logging + metrics
  core/                # events, event_bus, task_queue, runtime (kernel)
  memory/              # engine + vector_store (chroma | in-memory)
  llm/                 # pluggable provider (mock | anthropic | gemini)
  tools/               # registry + base + builtin tools
  skills/              # skill registry
  permissions/         # capability manager
  knowledge/           # knowledge graph
  reflection/          # reflection engine
  agents/              # base agent + specialist roster
  orchestrator/        # data-driven execution loop (+ langgraph builder)
  api/                 # FastAPI app, routes, schemas
web/                   # zero-build Web UI console
tests/                 # 38 tests across every subsystem
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for design rationale and the extension
guide (custom agents, tools, skills, phases, and MCP servers).

---

## Status & roadmap

This is **milestone 1**: a fully working, tested kernel + agent roster + loop +
API/UI + Docker. Next milestones are tracked in `ARCHITECTURE.md` → *Roadmap*
(LangGraph streaming, MCP client, Postgres-backed durable memory, plugin
auto-discovery, parallel multi-agent phases).

## License

MIT License
