"""API routes. All endpoints operate on the shared Runtime stored in app.state."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from genesis.api.schemas import (
    MemoryRequest,
    RecallQuery,
    RunRequest,
    TaskRequest,
    ToolInvokeRequest,
)
from genesis.core.runtime import Runtime
from genesis.observability import METRICS

router = APIRouter()


def _rt(request: Request) -> Runtime:
    return request.app.state.runtime


@router.get("/health", tags=["system"])
async def health(request: Request) -> dict:
    return _rt(request).health()


@router.get("/metrics", tags=["system"])
async def metrics() -> dict:
    return METRICS.snapshot()


@router.get("/events", tags=["system"])
async def events(request: Request, limit: int = 50, topic: str | None = None) -> dict:
    items = _rt(request).bus.history(limit=limit, topic=topic)
    return {"events": [e.model_dump(mode="json") for e in items]}


@router.post("/runs", tags=["execution"])
async def create_run(request: Request, body: RunRequest) -> dict:
    result = await _rt(request).run_goal(body.goal, body.context)
    return result.model_dump(mode="json")


@router.post("/tasks", tags=["execution"])
async def create_task(request: Request, body: TaskRequest) -> dict:
    task = await _rt(request).submit_task(body.goal, body.priority, **body.context)
    return task.model_dump(mode="json")


@router.get("/tasks", tags=["execution"])
async def list_tasks(request: Request) -> dict:
    return {"tasks": [t.model_dump(mode="json") for t in _rt(request).tasks.all()]}


@router.get("/tasks/{task_id}", tags=["execution"])
async def get_task(request: Request, task_id: str) -> dict:
    task = _rt(request).tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task.model_dump(mode="json")


@router.get("/agents", tags=["agents"])
async def list_agents(request: Request) -> dict:
    agents = _rt(request).agents
    return {"agents": [{"role": r, "prompt": a.system_prompt} for r, a in agents.items()]}


@router.get("/tools", tags=["tools"])
async def list_tools(request: Request) -> dict:
    return {"tools": _rt(request).tools.schemas()}


@router.post("/tools/{name}/invoke", tags=["tools"])
async def invoke_tool(request: Request, name: str, body: ToolInvokeRequest) -> dict:
    result = await _rt(request).tools.invoke(name, principal="api", **body.arguments)
    return result.model_dump()


@router.post("/memory", tags=["memory"])
async def store_memory(request: Request, body: MemoryRequest) -> dict:
    rec = await _rt(request).memory.store(body.content, kind=body.kind, tags=body.tags)
    return rec.model_dump(mode="json")


@router.post("/memory/recall", tags=["memory"])
async def recall_memory(request: Request, body: RecallQuery) -> dict:
    recs = _rt(request).memory.recall(body.query, k=body.k, kind=body.kind)
    return {"results": [r.model_dump(mode="json") for r in recs]}
