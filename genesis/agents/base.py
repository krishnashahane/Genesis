"""Base Agent — common machinery for every specialist agent.

Each agent is a thin, role-specialised wrapper around the shared kernel
services (LLM, memory, tools, event bus). The base class implements the full
"act" lifecycle so concrete agents only declare *who they are* (role + system
prompt) and optionally override how they build their prompt or post-process
output. This keeps agents uniform, testable, and free of hardcoded workflow.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from genesis.core.event_bus import EventBus
from genesis.core.events import Event, EventType
from genesis.llm.provider import LLMProvider, Message
from genesis.memory.engine import MemoryEngine
from genesis.observability import METRICS, get_logger
from genesis.tools.registry import ToolRegistry

log = get_logger("genesis.agents")


class AgentContext(BaseModel):
    """Everything an agent needs to know to act on one loop phase."""

    goal: str
    phase: str
    correlation_id: str | None = None
    blackboard: dict[str, Any] = Field(default_factory=dict)  # shared run state


class AgentResult(BaseModel):
    agent: str
    phase: str
    output: str
    artifacts: dict[str, Any] = Field(default_factory=dict)


class Agent:
    """Generic agent. Subclasses set ``role`` and ``system_prompt``."""

    role: str = "agent"
    system_prompt: str = "You are a helpful autonomous agent."
    #: capability checked before this agent may run.
    permission: str = "agent.run"
    #: number of recalled long-term memories injected into the prompt.
    recall_k: int = 4

    def __init__(
        self,
        llm: LLMProvider,
        memory: MemoryEngine,
        bus: EventBus,
        tools: ToolRegistry,
    ) -> None:
        self.llm = llm
        self.memory = memory
        self.bus = bus
        self.tools = tools

    # --- prompt construction (override to customize) ---
    def build_messages(self, ctx: AgentContext) -> list[Message]:
        recalled = self.memory.recall(ctx.goal, k=self.recall_k)
        memory_block = "\n".join(f"- {m.content}" for m in recalled) or "(no relevant memories)"
        prior = ctx.blackboard.get("last_output", "")
        prior_block = f"\n\nPrevious phase output:\n{prior}" if prior else ""
        user = (
            f"Goal: {ctx.goal}\n"
            f"Current phase: {ctx.phase}\n\n"
            f"Relevant long-term memory:\n{memory_block}"
            f"{prior_block}\n\n"
            f"Produce your {self.phase_objective()}."
        )
        return [
            Message(role="system", content=self.system_prompt),
            Message(role="user", content=user),
        ]

    def phase_objective(self) -> str:
        return "result for this phase"

    # --- post-processing (override to extract artifacts) ---
    def parse_output(self, raw: str, ctx: AgentContext) -> AgentResult:
        return AgentResult(agent=self.role, phase=ctx.phase, output=raw)

    # --- the lifecycle ---
    async def act(self, ctx: AgentContext) -> AgentResult:
        await self.bus.publish(
            Event(type=EventType.AGENT_STARTED, source=self.role,
                  correlation_id=ctx.correlation_id, payload={"phase": ctx.phase})
        )
        METRICS.incr(f"agent.{self.role}.runs")
        try:
            with METRICS.timer(f"agent.{self.role}.act"):
                raw = await self.llm.complete(self.build_messages(ctx))
            result = self.parse_output(raw, ctx)
        except Exception as exc:
            log.error("agent.error", role=self.role, error=str(exc))
            await self.bus.publish(
                Event(type=EventType.AGENT_ERROR, source=self.role,
                      correlation_id=ctx.correlation_id, payload={"error": str(exc)})
            )
            raise

        await self.bus.publish(
            Event(type=EventType.AGENT_FINISHED, source=self.role,
                  correlation_id=ctx.correlation_id,
                  payload={"phase": ctx.phase, "chars": len(result.output)})
        )
        return result

    async def message(self, to: str, content: str, correlation_id: str | None = None) -> None:
        """Agent-to-agent communication via the event bus."""
        await self.bus.publish(
            Event(type=EventType.AGENT_MESSAGE, source=self.role,
                  correlation_id=correlation_id, payload={"to": to, "content": content})
        )
