# Genesis — Architecture

Genesis is a small, dependency-injected runtime kernel for autonomous agent workflows. The implementation favors explicit interfaces, local defaults, and replaceable backends.

## Design principles

1. Event-driven communication through the shared EventBus.
2. Data-driven workflows through a list of `Phase` objects.
3. Graceful degradation to in-memory services and the mock LLM.
4. Dependency injection through the Runtime object.
5. Uniform specialist agents built on one Agent base class.

## Subsystems

~~~text
Runtime
├── observability
├── EventBus              optional Redis mirror
├── PermissionManager
├── MemoryEngine          ChromaVectorStore | InMemoryVectorStore
├── ToolRegistry          calculator | echo
├── SkillRegistry
├── KnowledgeGraph
├── LLM provider          Mock | Anthropic | Gemini
├── ReflectionEngine
├── TaskQueue
├── agents
└── ExecutionLoop
~~~

## Execution loop

`ExecutionLoop.run(goal)`:

1. Emits `loop.started`.
2. Seeds short-term memory with the goal and prior reflections.
3. Walks the configured phase list.
4. Each agent recalls relevant memory, calls the selected LLM, threads output through the blackboard, and stores episodic memory.
5. Reflection stores a reusable lesson for future runs.
6. Emits `loop.finished` and clears short-term memory.

## Memory model

- Working memory: bounded in-process deque.
- Long-term memory: pluggable vector store.
- ChromaDB: optional persistent backend.
- In-memory fallback: deterministic BLAKE2b token hashing + cosine similarity.

## Security boundary

- The API binds to localhost by default.
- Production mode requires `GENESIS_API_KEY`.
- API requests are size-limited and rate-limited.
- CORS is allowlist-based.
- Tool invocations are capability-checked before execution.
- API agent introspection does not expose system prompts.

## Extending Genesis

### Add a tool

Register an async `Tool` with a JSON-schema parameter definition and an explicit permission capability.

### Add an agent

Subclass `Agent`, define its role/system prompt/phase objective, then add it to the roster.

### Change the workflow

Pass a custom list of `Phase` objects to `Runtime.run_goal`.

### Swap providers/backends

Use the `GENESIS_` environment variables documented in `README.md`.

## Roadmap

- LangGraph execution and streaming
- MCP client integration
- Durable memory adapters
- Parallel phase execution
- Plugin discovery
- Multi-tenant authentication
