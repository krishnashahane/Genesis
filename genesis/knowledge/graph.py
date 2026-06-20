"""Knowledge Graph — a lightweight, in-memory entity/relationship store.

Captures structured facts agents learn ("FileX implements ComponentY",
"BugZ caused-by NullCheck") as a directed labelled graph. Dependency-free
adjacency lists; a Neo4j/Postgres backend can replace the internals behind the
same query methods later.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from pydantic import BaseModel, Field


class Triple(BaseModel):
    subject: str
    predicate: str
    obj: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraph:
    def __init__(self) -> None:
        self._triples: list[Triple] = []
        self._out: dict[str, list[Triple]] = defaultdict(list)
        self._in: dict[str, list[Triple]] = defaultdict(list)

    def add(self, subject: str, predicate: str, obj: str, **meta: Any) -> Triple:
        t = Triple(subject=subject, predicate=predicate, obj=obj, metadata=dict(meta))
        self._triples.append(t)
        self._out[subject].append(t)
        self._in[obj].append(t)
        return t

    def neighbors(self, node: str) -> list[Triple]:
        """All edges touching ``node`` (outgoing + incoming)."""
        return [*self._out.get(node, []), *self._in.get(node, [])]

    def query(
        self, subject: str | None = None, predicate: str | None = None, obj: str | None = None
    ) -> list[Triple]:
        return [
            t
            for t in self._triples
            if (subject is None or t.subject == subject)
            and (predicate is None or t.predicate == predicate)
            and (obj is None or t.obj == obj)
        ]

    @property
    def size(self) -> int:
        return len(self._triples)
