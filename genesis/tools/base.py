"""Tool abstraction — the unit of capability an agent can invoke.

A Tool is a named, described, async-callable with a JSON-schema-ish parameter
spec. This same shape maps cleanly onto MCP tools and LLM function-calling, so
external tools / MCP servers register through the very same interface.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    ok: bool
    output: Any = None
    error: str | None = None


class Tool(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)  # JSON-schema style
    # the actual implementation (async). Excluded from serialization.
    handler: Callable[..., Awaitable[ToolResult]] = Field(exclude=True, repr=False)
    # capability tag checked by the Permission System before execution
    permission: str = "tool.execute"

    model_config = {"arbitrary_types_allowed": True}

    async def __call__(self, **kwargs: Any) -> ToolResult:
        return await self.handler(**kwargs)

    def schema(self) -> dict[str, Any]:
        """LLM/MCP-compatible tool schema (without the handler)."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
