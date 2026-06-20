"""Skill System — reusable, composable procedures above raw tools.

Where a *tool* is a single capability, a *skill* is a learned/authored procedure
(often chaining tools, memory lookups, and LLM calls) that the system can grow
over time. Skills are the substrate for self-improvement: the Reflection Engine
can propose new skills, and the plugin system can ship them.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field

from genesis.observability import get_logger

log = get_logger("genesis.skills")

SkillFn = Callable[..., Awaitable[Any]]


class Skill(BaseModel):
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    fn: SkillFn = Field(exclude=True, repr=False)

    model_config = {"arbitrary_types_allowed": True}

    async def run(self, **kwargs: Any) -> Any:
        return await self.fn(**kwargs)


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill
        log.info("skill.registered", name=skill.name)

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list(self) -> list[Skill]:
        return list(self._skills.values())

    def find(self, tag: str) -> list[Skill]:
        return [s for s in self._skills.values() if tag in s.tags]
