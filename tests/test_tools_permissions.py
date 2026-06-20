import pytest

from genesis.core.event_bus import EventBus
from genesis.permissions.manager import PermissionManager
from genesis.tools.builtin import builtin_tools
from genesis.tools.registry import ToolRegistry


@pytest.fixture
def registry() -> ToolRegistry:
    perms = PermissionManager()
    perms.grant("agent", "tool.*")
    reg = ToolRegistry(EventBus(), perms)
    for tool in builtin_tools():
        reg.register(tool)
    return reg


async def test_calculator_tool(registry: ToolRegistry):
    res = await registry.invoke("calculator", principal="agent", expression="2 + 3 * 4")
    assert res.ok
    assert res.output == 14.0


async def test_calculator_rejects_unsafe(registry: ToolRegistry):
    res = await registry.invoke("calculator", principal="agent", expression="__import__('os')")
    assert not res.ok


async def test_unknown_tool(registry: ToolRegistry):
    res = await registry.invoke("nope", principal="agent")
    assert not res.ok
    assert "unknown" in res.error


async def test_permission_denied():
    perms = PermissionManager()  # no grants for "stranger"
    reg = ToolRegistry(EventBus(), perms)
    for tool in builtin_tools():
        reg.register(tool)
    res = await reg.invoke("echo", principal="stranger", text="hi")
    assert not res.ok
    assert "permission denied" in res.error


def test_wildcard_permission():
    perms = PermissionManager()
    perms.grant("a", "tool.*")
    assert perms.allowed("a", "tool.execute")
    assert not perms.allowed("a", "memory.write")


def test_duplicate_registration_fails():
    reg = ToolRegistry(EventBus(), PermissionManager())
    tools = builtin_tools()
    reg.register(tools[0])
    with pytest.raises(ValueError):
        reg.register(tools[0])
