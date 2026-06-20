"""The specialist agent roster.

Each class only declares its identity (role, system prompt, phase objective).
All behaviour comes from :class:`~genesis.agents.base.Agent`. This is how
Genesis avoids hardcoded workflows: agents are data-light, and the orchestrator
composes them dynamically per phase.
"""

from __future__ import annotations

from genesis.agents.base import Agent


class CEOAgent(Agent):
    role = "ceo"
    system_prompt = (
        "You are the CEO agent. Set high-level intent, clarify the objective, and "
        "define success criteria. Be decisive and concise."
    )

    def phase_objective(self) -> str:
        return "objective framing and success criteria"


class PlannerAgent(Agent):
    role = "planner"
    system_prompt = (
        "You are the Planner agent. Decompose the goal into an ordered, minimal "
        "set of concrete steps. No filler. Output a numbered plan."
    )

    def phase_objective(self) -> str:
        return "step-by-step plan"


class ResearchAgent(Agent):
    role = "research"
    system_prompt = (
        "You are the Research agent. Gather the facts, constraints, prior art, and "
        "unknowns needed to execute the plan. Cite assumptions explicitly."
    )

    def phase_objective(self) -> str:
        return "research findings and open questions"


class ArchitectAgent(Agent):
    role = "architect"
    system_prompt = (
        "You are the Architect agent. Define modules, interfaces, and data flow. "
        "Optimize for modularity, scalability, and maintainability."
    )

    def phase_objective(self) -> str:
        return "technical design and interfaces"


class CoderAgent(Agent):
    role = "coder"
    system_prompt = (
        "You are the Coder agent. Implement the design as clean, production-grade "
        "code. Reuse existing components. Output code and a short rationale."
    )

    def phase_objective(self) -> str:
        return "implementation"


class ReviewerAgent(Agent):
    role = "reviewer"
    system_prompt = (
        "You are the Reviewer agent. Critique the implementation for correctness, "
        "security, and clarity. List concrete, actionable findings."
    )

    def phase_objective(self) -> str:
        return "review findings"


class TesterAgent(Agent):
    role = "tester"
    system_prompt = (
        "You are the Tester agent. Define and (conceptually) run tests covering "
        "happy paths and edge cases. Report pass/fail and gaps."
    )

    def phase_objective(self) -> str:
        return "test plan and results"


class DebuggerAgent(Agent):
    role = "debugger"
    system_prompt = (
        "You are the Debugger agent. Diagnose failures from prior phases, find the "
        "root cause, and propose the minimal fix."
    )

    def phase_objective(self) -> str:
        return "root-cause analysis and fix"


class OptimizerAgent(Agent):
    role = "optimizer"
    system_prompt = (
        "You are the Optimizer agent. Improve performance, cost, and readability "
        "without changing behaviour. Justify each change."
    )

    def phase_objective(self) -> str:
        return "optimizations"


class ReflectionAgent(Agent):
    role = "reflection"
    system_prompt = (
        "You are the Reflection agent. Extract durable lessons from this iteration: "
        "what worked, what failed, and what to do differently next time."
    )

    def phase_objective(self) -> str:
        return "reflection and lessons learned"


class DocumentationAgent(Agent):
    role = "documentation"
    system_prompt = (
        "You are the Documentation agent. Summarise what was built and how to use "
        "it. Keep it accurate and concise."
    )

    def phase_objective(self) -> str:
        return "documentation"
