import pytest
from fastapi.testclient import TestClient

from genesis.api.app import create_app
from genesis.config import Settings
from genesis.core.runtime import Runtime


@pytest.fixture
def client():
    rt = Runtime(Settings(env="test", llm_provider="mock"))
    app = create_app(runtime=rt)
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["llm"] == "mock"


def test_create_run(client):
    r = client.post("/api/runs", json={"goal": "Design a cache"})
    assert r.status_code == 200
    body = r.json()
    assert body["goal"] == "Design a cache"
    assert len(body["phases"]) >= 1
    assert body["reflection"]


def test_task_lifecycle(client):
    r = client.post("/api/tasks", json={"goal": "do thing", "priority": 1})
    assert r.status_code == 200
    task_id = r.json()["id"]
    assert client.get(f"/api/tasks/{task_id}").status_code == 200
    assert client.get("/api/tasks/missing").status_code == 404


def test_tools_endpoints(client):
    tools = client.get("/api/tools").json()["tools"]
    assert any(t["name"] == "calculator" for t in tools)
    r = client.post("/api/tools/calculator/invoke", json={"arguments": {"expression": "6*7"}})
    assert r.json()["output"] == 42.0


def test_memory_endpoints(client):
    client.post("/api/memory", json={"content": "Genesis uses an event bus", "kind": "semantic"})
    r = client.post("/api/memory/recall", json={"query": "event bus", "k": 3})
    assert r.status_code == 200
    assert r.json()["results"]


def test_agents_and_metrics(client):
    assert len(client.get("/api/agents").json()["agents"]) == 11
    assert "counters" in client.get("/api/metrics").json()


def test_events_feed(client):
    client.post("/api/runs", json={"goal": "emit some events"})
    r = client.get("/api/events?limit=10")
    assert r.status_code == 200
    assert r.json()["events"]
