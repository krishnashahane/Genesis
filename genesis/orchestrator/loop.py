"""Execution Loop — Observe → Plan → … → Reflect → Store Memory.

The loop is **data-driven**: it's a list of :class:`Phase` objects mapping a
phase name to an agent role. There is no hardcoded ``if phase == "plan"`` logic
anywhere — callers can reorder, add, or remove phases (or pass their own list)
to change the workflow entirely. Each phase:

1. builds an :class:`AgentContext` from the goal + shared blackboard,
2. runs the mapped agent,
3. threads the output forward and persists it to long-term memory.

After the final phase the Reflection Engine distils a lesson for next time.

When ``langgraph`` is installed the same phase list is compiled into a LangGraph
``StateGraph`` (see :func:`build_langgraph`) for visualization/streaming; the
plain async path below is the dependency-free default used in tests.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from genesis.agents.base import Agent, AgentContext
from genesis.core.event_bus import EventBus
from genesis.core.events import Event, EventType
from genesis.memory.engine import MemoryEngine
from genesis.observability import METRICS, get_logger
from genesis.reflection.engine import ReflectionEngine

log = get_logger("genesis.orchestrator")


class Phase(BaseModel):
    name: str
    agent_role: str
    #: if True, the loop continues even when this agent errors (best-effort phase)
    optional: bool = False


#: The canonical Genesis workflow. Override by passing your own list.
DEFAULT_PHASES: list[Phase] = [
    Phase(name="observe", agent_role="ceo"),
    Phase(name="plan", agent_role="planner"),
    Phase(name="research", agent_role="research"),
    Phase(name="design", agent_role="architect"),
    Phase(name="build", agent_role="coder"),
    Phase(name="review", agent_role="reviewer"),
    Phase(name="test", agent_role="tester"),
    Phase(name="debug", agent_role="debugger", optional=True),
    Phase(name="optimize", agent_role="optimizer", optional=True),
    Phase(name="document", agent_role="documentation", optional=True),
]


class PhaseOutput(BaseModel):
    phase: str
    agent: str
    output: str


class RunResult(BaseModel):
    run_id: str
    goal: str
    phases: list[PhaseOutput] = Field(default_factory=list)
    reflection: str | None = None
    blackboard: dict[str, Any] = Field(default_factory=dict)


class ExecutionLoop:
    def __init__(
        self,
        agents: dict[str, Agent],
        memory: MemoryEngine,
        bus: EventBus,
        reflection: ReflectionEngine,
        phases: list[Phase] | None = None,
    ) -> None:
        self._agents = agents
        self._memory = memory
        self._bus = bus
        self._reflection = reflection
        self._phases = phases or DEFAULT_PHASES

    async def run(self, goal: str, context: dict[str, Any] | None = None) -> RunResult:
        run_id = uuid.uuid4().hex
        blackboard: dict[str, Any] = dict(context or {})
        result = RunResult(run_id=run_id, goal=goal)

        await self._bus.publish(
            Event(type=EventType.LOOP_STARTED, source="orchestrator",
                  correlation_id=run_id, payload={"goal": goal})
        )
        # Observe: seed working memory with the goal and recalled lessons.
        self._memory.remember_short(f"goal: {goal}")
        for lesson in self._reflection.past_lessons(goal):
            self._memory.remember_short(lesson.content)

        with METRICS.timer("loop.run"):
            for phase in self._phases:
                agent = self._agents.get(phase.agent_role)
                if agent is None:
                    log.warning("loop.missing_agent", role=phase.agent_role)
                    continue

                await self._bus.publish(
                    Event(type=EventType.PHASE_STARTED, source="orchestrator",
                          correlation_id=run_id, payload={"phase": phase.name})
                )
                ctx = AgentContext(
                    goal=goal, phase=phase.name, correlation_id=run_id, blackboard=blackboard
                )
                try:
                    agent_result = await agent.act(ctx)
                except Exception as exc:
                    if phase.optional:
                        log.warning("loop.phase_skipped", phase=phase.name, error=str(exc))
                        continue
                    await self._bus.publish(
                        Event(
                            type=EventType.LOOP_FINISHED, source="orchestrator",
                            correlation_id=run_id,
                            payload={"status": "failed", "phase": phase.name},
                        )
                    )
                    raise

                # thread output forward + persist
                blackboard["last_output"] = agent_result.output
                blackboard[f"phase.{phase.name}"] = agent_result.output
                result.phases.append(
                    PhaseOutput(
                        phase=phase.name, agent=agent_result.agent, output=agent_result.output
                    )
                )
                await self._memory.store(
                    f"[{phase.name}] {agent_result.output}",
                    kind="episodic",
                    tags=[phase.name, agent_result.agent],
                    run_id=run_id,
                )
                await self._bus.publish(
                    Event(type=EventType.PHASE_FINISHED, source="orchestrator",
                          correlation_id=run_id, payload={"phase": phase.name})
                )

        # Reflect → Store Memory
        summary = self._summarize(result)
        reflection = await self._reflection.reflect(goal, summary, correlation_id=run_id)
        result.reflection = reflection.content
        result.blackboard = blackboard

        await self._bus.publish(
            Event(type=EventType.LOOP_FINISHED, source="orchestrator", correlation_id=run_id,
                  payload={"status": "completed", "phases": len(result.phases)})
        )
        self._memory.clear_short()
        return result

    @staticmethod
    def _summarize(result: RunResult) -> str:
        done = ", ".join(p.phase for p in result.phases)
        return f"Completed {len(result.phases)} phases ({done})."


def build_langgraph(loop: ExecutionLoop):  # pragma: no cover - requires langgraph
    """Compile the loop's phases into a LangGraph StateGraph (optional).

    Returns a compiled graph whose nodes mirror :attr:`ExecutionLoop._phases`.
    Used for streaming/visualization when ``langgraph`` is installed.
    """
    from langgraph.graph import END, START, StateGraph

    graph: StateGraph = StateGraph(dict)

    def make_node(phase: Phase):
        async def _node(state: dict) -> dict:
            agent = loop._agents[phase.agent_role]
            ctx = AgentContext(goal=state["goal"], phase=phase.name,
                               correlation_id=state.get("run_id"), blackboard=state)
            res = await agent.act(ctx)
            state["last_output"] = res.output
            return state

        return _node

    prev = START
    for phase in loop._phases:
        graph.add_node(phase.name, make_node(phase))
        graph.add_edge(prev, phase.name)
        prev = phase.name
    graph.add_edge(prev, END)
    return graph.compile()
