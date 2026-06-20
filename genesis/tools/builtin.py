"""Built-in tools shipped with Genesis. Safe, dependency-free examples that also
serve as templates for plugin authors and MCP adapters."""

from __future__ import annotations

import ast
import operator
from typing import Any

from genesis.tools.base import Tool, ToolResult

# A deliberately small, safe arithmetic evaluator (no eval, no names/calls).
_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("unsupported expression")


async def _calc(expression: str = "", **_: object) -> ToolResult:
    try:
        tree = ast.parse(expression, mode="eval")
        return ToolResult(ok=True, output=_eval_node(tree.body))
    except Exception as exc:
        return ToolResult(ok=False, error=f"calc error: {exc}")


async def _echo(text: str = "", **_: object) -> ToolResult:
    return ToolResult(ok=True, output=text)


def builtin_tools() -> list[Tool]:
    return [
        Tool(
            name="calculator",
            description="Evaluate a basic arithmetic expression (+, -, *, /, **, %).",
            parameters={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
            handler=_calc,
        ),
        Tool(
            name="echo",
            description="Return the provided text unchanged. Useful for testing.",
            parameters={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
            handler=_echo,
        ),
    ]
