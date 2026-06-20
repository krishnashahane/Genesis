"""Runtime — the Genesis kernel.

Boots and wires every subsystem into one cohesive object graph: observability,
event bus, permissions, memory, tools, skills, knowledge graph, the agent
roster, the reflection engine, and the execution loop. The API and CLI both
talk to a single ``Runtime`` instance.

Construction is dependency-injection friendly: every collaborator can be passed
in (for tests), otherwise sensible defaults are built from Settings.
"""

from __future__ import annotations

from typing import Any

from genesis.agents.base import Agent
from genesis.agents.roster import build_roster
from genesis.config import Settings, get_settings
from genesis.core.event_bus import EventBus
from genesis.core.task_queue import Task, TaskQueue
from genesis.knowledge.graph import KnowledgeGraph
from genesis.llm.provider import LLMProvider, build_llm
from genesis.memory.engine import MemoryEngine
from genesis.observability import configure_logging, get_logger
from genesis.orchestrator.loop import ExecutionLoop, Phase, RunResult
from genesis.permissions.manager import PermissionManager
from genesis.reflection.engine import ReflectionEngine
from genesis.skills.registry import SkillRegistry
from genesis.tools.builtin import builtin_tools
from genesis.tools.registry import ToolRegistry

log = get_logger("genesis.runtime")


class Runtime:
    def __init__(self, settings: Settings | None = None, llm: LLMProvider | None = None) -> None:
        self.settings = settings or get_settings()
        configure_logging(self.settings.log_level)

        # Kernel services
        self.bus = EventBus(redis_url=self.settings.redis_url)
        self.permissions = PermissionManager()
        self.memory = MemoryEngine(self.bus, chroma_path=self.settings.chroma_path)
        self.tools = ToolRegistry(self.bus, self.permissions)
        self.skills = SkillRegistry()
        self.knowledge = KnowledgeGraph()
        self.llm = llm or build_llm(self.settings)

        # Higher-level services
        self.reflection = ReflectionEngine(self.memory, self.bus)
        self.agents: dict[str, Agent] = build_roster(self.llm, self.memory, self.bus, self.tools)
        self.tasks = TaskQueue(self.bus)
        self.loop = ExecutionLoop(self.agents, self.memory, self.bus, self.reflection)

        self._register_builtins()
        self._grant_default_permissions()
        self._started = False

    def _register_builtins(self) -> None:
        for tool in builtin_tools():
            self.tools.register(tool)

    def _grant_default_permissions(self) -> None:
        # Every agent may run and use tools by default; tighten per deployment.
        for role in self.agents:
            self.permissions.grant(role, "agent.run")
            self.permissions.grant(role, "tool.*")
        # The REST API acts as a trusted principal for direct tool invocation.
        self.permissions.grant("api", "tool.*")

    async def start(self) -> None:
        if self._started:
            return
        await self.bus.connect()
        self._started = True
        log.info(
            "runtime.started",
            llm=self.llm.name,
            agents=len(self.agents),
            tools=len(self.tools.list()),
        )

    async def stop(self) -> None:
        await self.bus.close()
        self._started = False
        log.info("runtime.stopped")

    # --- high-level operations ---
    async def run_goal(
        self, goal: str, context: dict[str, Any] | None = None, phases: list[Phase] | None = None
    ) -> RunResult:
        """Execute the full loop for a goal. Optionally override the phase list."""
        loop = self.loop if phases is None else ExecutionLoop(
            self.agents, self.memory, self.bus, self.reflection, phases=phases
        )
        return await loop.run(goal, context)

    async def submit_task(self, goal: str, priority: int = 0, **context: Any) -> Task:
        return await self.tasks.submit(Task(goal=goal, priority=priority, context=context))

    async def process_next_task(self) -> RunResult:
        """Claim one queued task, run the loop, and record the outcome."""
        task = await self.tasks.claim()
        try:
            result = await self.run_goal(task.goal, task.context)
            await self.tasks.complete(
                task.id, {"run_id": result.run_id, "phases": len(result.phases)}
            )
            return result
        except Exception as exc:
            await self.tasks.fail(task.id, str(exc))
            raise

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self._started else "initialized",
            "env": self.settings.env,
            "llm": self.llm.name,
            "agents": list(self.agents),
            "tools": [t.name for t in self.tools.list()],
            "memory_long_term": self.memory.long_term_count,
            "pending_tasks": self.tasks.pending,
            "knowledge_triples": self.knowledge.size,
        }
