"""Tool Registry — discover, register, and execute tools with permission checks.

Every tool invocation is permission-gated and emitted on the event bus, giving
the Observability layer a complete audit trail of capability use.
"""

from __future__ import annotations

from genesis.core.event_bus import EventBus
from genesis.core.events import Event, EventType
from genesis.observability import METRICS, get_logger
from genesis.permissions.manager import PermissionManager
from genesis.tools.base import Tool, ToolResult

log = get_logger("genesis.tools.registry")


class ToolRegistry:
    def __init__(self, bus: EventBus, permissions: PermissionManager) -> None:
        self._bus = bus
        self._permissions = permissions
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool
        log.info("tool.registered", name=tool.name)

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list(self) -> list[Tool]:
        return list(self._tools.values())

    def schemas(self) -> list[dict]:
        return [t.schema() for t in self._tools.values()]

    async def invoke(self, name: str, principal: str = "system", **kwargs: object) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(ok=False, error=f"unknown tool: {name}")

        if not self._permissions.allowed(principal, tool.permission):
            await self._bus.publish(
                Event(type=EventType.PERMISSION_DENIED, source="tool_registry",
                      payload={"tool": name, "principal": principal, "perm": tool.permission})
            )
            return ToolResult(ok=False, error=f"permission denied: {tool.permission}")

        await self._bus.publish(
            Event(type=EventType.TOOL_INVOKED, source="tool_registry",
                  payload={"tool": name, "principal": principal})
        )
        METRICS.incr("tools.invoked")
        try:
            with METRICS.timer(f"tool.{name}"):
                return await tool(**kwargs)
        except Exception as exc:  # a failing tool must not crash the runtime
            log.error("tool.error", name=name, error=str(exc))
            METRICS.incr("tools.errors")
            return ToolResult(ok=False, error=str(exc))
