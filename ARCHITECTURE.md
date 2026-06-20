# Genesis — Architecture

This document explains *why* Genesis is built the way it is, and how to extend
it. For a usage quickstart see [`README.md`](README.md).

## Design principles

1. **Event-driven, never point-to-point.** Subsystems and agents communicate by
   publishing typed `Event`s on the `EventBus`. Nothing imports another agent to
   call it. This keeps the graph decoupled, makes everything observable, and lets
   new subscribers (UI, metrics, external sinks) attach without touching producers.

2. **Data-driven workflows, no hardcoded branching.** The execution loop is a
   *list* of `Phase(name, agent_role)` objects (`DEFAULT_PHASES`). The loop body
   contains zero `if phase == "..."` logic. Change the list → change the workflow.
   Callers may pass a custom phase list per run.

3. **Graceful degradation.** Every external backend (Redis, PostgreSQL, ChromaDB)
   and every LLM provider has an in-memory / mock fallback selected at runtime.
   The system always boots; production simply swaps backends via env vars. Call
   sites never change because each backend hides behind a narrow interface.

4. **Dependency injection at the kernel.** `Runtime` constructs and owns every
   subsystem and injects shared services into agents. Tests build a `Runtime`
   with a `mock` provider and in-memory stores — no network, fully deterministic.

5. **Uniform agents.** Behaviour lives in `Agent` (the base class). A specialist
   only declares its identity (role + system prompt + phase objective). This makes
   agents trivial to add, review, and test, and keeps prompt logic in one place.

## Subsystem map

```
Runtime
├── observability     configure_logging + METRICS (counters/timers) + event history
├── EventBus          async pub/sub, topic + "*" wildcard, optional Redis mirror
├── PermissionManager capability grants with wildcard matching ("tool.*", "*")
├── MemoryEngine
│   ├── short-term    bounded deque (working memory, cleared per run)
│   └── long-term     VectorStore: ChromaVectorStore | InMemoryVectorStore
├── ToolRegistry      permission-gated, audited; emits tool.invoked
│   └── builtin       calculator (safe AST eval), echo
├── SkillRegistry     composable procedures above tools (self-improvement substrate)
├── KnowledgeGraph    subject-predicate-object triples + adjacency queries
├── LLM provider      MockProvider | AnthropicProvider | GeminiProvider
├── ReflectionEngine  store/recall "lesson" memories; closes the learning loop
├── TaskQueue         priority asyncio queue; emits task.* lifecycle events
├── agents            role → Agent (11 specialists)
└── ExecutionLoop     walks phases; per phase: recall → act → emit → persist
```

## The execution loop in detail

`ExecutionLoop.run(goal)`:

1. Emit `loop.started`. Seed short-term memory with the goal and any recalled
   **reflections** for this goal (so past lessons influence this run).
2. For each `Phase`:
   - Resolve the mapped agent (skip with a warning if absent).
   - Emit `phase.started`; build an `AgentContext` (goal, phase, blackboard).
   - `agent.act()` → recall long-term memory → build messages → call the LLM →
     parse output → emit `agent.started`/`agent.finished`.
   - Thread `last_output` onto the blackboard and **persist** the phase output as
     an `episodic` memory (tagged with phase + agent).
   - Emit `phase.finished`. `optional` phases that error are skipped, not fatal.
3. **Reflect**: summarise the run, store a `reflection` memory, emit
   `reflection.created`.
4. Emit `loop.finished`; clear short-term memory; return a `RunResult` with every
   phase output, the reflection, and the final blackboard.

### Memory model

- **Short-term (working)**: a `deque(maxlen=N)` — fast, ephemeral, per-run.
- **Long-term (persistent)**: vector store with three kinds:
  - `episodic` — what happened (each phase output),
  - `semantic` — facts (user-supplied or learned),
  - `reflection` — lessons used to self-improve.
- The in-memory fallback uses a deterministic hashing bag-of-words embedding +
  cosine similarity, so recall works offline and in tests. ChromaDB is used
  automatically when installed (`GENESIS_CHROMA_PATH`).

## Extending Genesis

### Add a tool
```python
from genesis.tools.base import Tool, ToolResult

async def handler(url: str = "", **_): ...
    return ToolResult(ok=True, output=...)

runtime.tools.register(Tool(
    name="fetch", description="HTTP GET a URL",
    parameters={"type": "object", "properties": {"url": {"type": "string"}}},
    handler=handler, permission="tool.execute",
))
```
Tool schemas are MCP/LLM-function-call compatible, so an MCP client adapter can
register remote tools through this same interface (roadmap item).

### Add an agent
Subclass `Agent`, set `role`, `system_prompt`, and `phase_objective()`, then add
it to `AGENT_CLASSES` in `genesis/agents/roster.py` and reference its role from a
`Phase`. No other wiring needed.

### Change the workflow
Pass a custom phase list:
```python
await runtime.run_goal("…", phases=[
    Phase(name="plan", agent_role="planner"),
    Phase(name="build", agent_role="coder"),
    Phase(name="review", agent_role="reviewer"),
])
```

### Add a skill
```python
runtime.skills.register(Skill(name="...", description="...", tags=[...], fn=async_fn))
```

### Swap the LLM / backends
All via env vars (`GENESIS_LLM_PROVIDER`, `GENESIS_REDIS_URL`,
`GENESIS_POSTGRES_DSN`, `GENESIS_CHROMA_PATH`). See `.env.example`.

## Observability

- Structured JSON logs to **stderr** (stdout stays clean for CLI/JSON payloads).
- `METRICS` records counters (`events.published`, `tools.invoked`, `llm.calls`, …)
  and timers (`loop.run`, `agent.<role>.act`, `tool.<name>`); exposed at
  `GET /api/metrics`.
- `EventBus` keeps a rolling history exposed at `GET /api/events` and streamed to
  the Web UI feed.

## Testing strategy

`tests/` covers each subsystem in isolation plus integration through the
`Runtime` and the FastAPI `TestClient`:
event bus semantics, memory recall/persistence, tool execution + permission
denial, task queue ordering, the full loop, agent lifecycle/messaging, and every
REST endpoint. The `mock` provider keeps tests deterministic and offline.

## Roadmap (next milestones)

1. **LangGraph streaming** — execute via the compiled `build_langgraph` graph for
   token/step streaming and visualization.
2. **MCP client** — register external MCP-server tools into the Tool Registry.
3. **Durable memory** — PostgreSQL-backed memory & task persistence behind the
   existing interfaces; Alembic migrations.
4. **Parallel phases** — fan-out phases (e.g. multiple reviewers) with result
   aggregation.
5. **Plugin auto-discovery** — entry-point-based discovery of third-party agents,
   tools, and skills.
6. **Auth & multi-tenant** — API auth + per-tenant permission scoping.
