"""Roster builder — instantiates every agent with shared kernel services."""

from __future__ import annotations

from genesis.agents.base import Agent
from genesis.agents.specialists import (
    ArchitectAgent,
    CEOAgent,
    CoderAgent,
    DebuggerAgent,
    DocumentationAgent,
    OptimizerAgent,
    PlannerAgent,
    ReflectionAgent,
    ResearchAgent,
    ReviewerAgent,
    TesterAgent,
)
from genesis.core.event_bus import EventBus
from genesis.llm.provider import LLMProvider
from genesis.memory.engine import MemoryEngine
from genesis.tools.registry import ToolRegistry

AGENT_CLASSES = [
    CEOAgent,
    PlannerAgent,
    ResearchAgent,
    ArchitectAgent,
    CoderAgent,
    ReviewerAgent,
    TesterAgent,
    DebuggerAgent,
    OptimizerAgent,
    ReflectionAgent,
    DocumentationAgent,
]


def build_roster(
    llm: LLMProvider, memory: MemoryEngine, bus: EventBus, tools: ToolRegistry
) -> dict[str, Agent]:
    """Return a ``role -> Agent`` mapping for the full roster."""
    return {cls.role: cls(llm, memory, bus, tools) for cls in AGENT_CLASSES}
