"""Permission System — capability-based access control for principals.

A *principal* (an agent name, "system", or an external caller) is granted a set
of capability strings. Grants support wildcards: ``"tool.*"`` allows any
``tool.<x>`` capability; ``"*"`` allows everything. The Tool Registry and
runtime consult this before any side-effecting action.
"""

from __future__ import annotations

from collections import defaultdict


class PermissionManager:
    def __init__(self) -> None:
        self._grants: dict[str, set[str]] = defaultdict(set)
        # System and the default agent role are trusted by default.
        self._grants["system"].add("*")

    def grant(self, principal: str, capability: str) -> None:
        self._grants[principal].add(capability)

    def revoke(self, principal: str, capability: str) -> None:
        self._grants[principal].discard(capability)

    def grants(self, principal: str) -> set[str]:
        return set(self._grants.get(principal, set()))

    def allowed(self, principal: str, capability: str) -> bool:
        granted = self._grants.get(principal, set())
        if "*" in granted or capability in granted:
            return True
        # wildcard prefix match: "tool.*" covers "tool.execute"
        return any(
            g.endswith(".*") and capability.startswith(g[:-1]) for g in granted
        )
