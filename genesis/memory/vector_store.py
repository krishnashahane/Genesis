"""Pluggable vector store for long-term memory.

Two backends behind one interface:

* ``ChromaVectorStore`` — persistent, used when ``chromadb`` is installed.
* ``InMemoryVectorStore`` — a dependency-free fallback using a deterministic
  bag-of-words hashing embedding + cosine similarity. Good enough for local dev
  and tests; swapped automatically when ChromaDB is unavailable.

The factory ``build_vector_store`` picks the best available backend.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Protocol

from genesis.memory.types import MemoryRecord
from genesis.observability import get_logger

log = get_logger("genesis.memory.vector_store")

_TOKEN = re.compile(r"[a-z0-9]+")
_EMBED_DIM = 256


def _embed(text: str) -> list[float]:
    """Deterministic hashing embedding — no model, no network, fully offline."""
    vec = [0.0] * _EMBED_DIM
    for token, count in Counter(_TOKEN.findall(text.lower())).items():
        vec[hash(token) % _EMBED_DIM] += float(count)
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


class VectorStore(Protocol):
    def add(self, record: MemoryRecord) -> None: ...
    def query(self, text: str, k: int, kind: str | None = None) -> list[MemoryRecord]: ...
    def count(self) -> int: ...


class InMemoryVectorStore:
    """Cosine-similarity store over hashing embeddings."""

    def __init__(self) -> None:
        self._records: list[tuple[list[float], MemoryRecord]] = []

    def add(self, record: MemoryRecord) -> None:
        self._records.append((_embed(record.content), record))

    def query(self, text: str, k: int, kind: str | None = None) -> list[MemoryRecord]:
        q = _embed(text)
        scored: list[MemoryRecord] = []
        for emb, rec in self._records:
            if kind and rec.kind != kind:
                continue
            r = rec.model_copy()
            r.score = round(_cosine(q, emb), 6)
            scored.append(r)
        scored.sort(key=lambda r: r.score or 0.0, reverse=True)
        return scored[:k]

    def count(self) -> int:
        return len(self._records)


class ChromaVectorStore:  # pragma: no cover - requires chromadb
    """Persistent ChromaDB-backed store."""

    def __init__(self, path: str, collection: str = "genesis_memory") -> None:
        import chromadb

        self._client = chromadb.PersistentClient(path=path)
        self._col = self._client.get_or_create_collection(collection)

    def add(self, record: MemoryRecord) -> None:
        self._col.add(
            ids=[record.id],
            documents=[record.content],
            metadatas=[{"kind": record.kind, "tags": ",".join(record.tags)}],
        )

    def query(self, text: str, k: int, kind: str | None = None) -> list[MemoryRecord]:
        where = {"kind": kind} if kind else None
        res = self._col.query(query_texts=[text], n_results=k, where=where)
        out: list[MemoryRecord] = []
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0], strict=False
        ):
            tags = meta.get("tags", "")
            out.append(
                MemoryRecord(
                    content=doc,
                    kind=meta.get("kind", "episodic"),
                    tags=tags.split(",") if tags else [],
                    score=round(1.0 - dist, 6),
                )
            )
        return out

    def count(self) -> int:
        return self._col.count()


def build_vector_store(chroma_path: str) -> VectorStore:
    """Return the best available vector store backend."""
    try:  # pragma: no cover - requires chromadb
        import chromadb  # noqa: F401

        log.info("memory.backend", backend="chromadb", path=chroma_path)
        return ChromaVectorStore(chroma_path)
    except Exception as exc:
        log.info("memory.backend", backend="in_memory", reason=str(exc))
        return InMemoryVectorStore()
