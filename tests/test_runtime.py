from genesis.core.task_queue import TaskStatus


async def test_health_reports_subsystems(runtime):
    h = runtime.health()
    assert h["status"] == "ok"
    assert h["llm"] == "mock"
    assert len(h["agents"]) == 11
    assert "calculator" in h["tools"]


async def test_submit_and_process_task(runtime):
    task = await runtime.submit_task("Summarize the codebase", priority=5)
    result = await runtime.process_next_task()
    assert result.goal == "Summarize the codebase"
    assert runtime.tasks.get(task.id).status is TaskStatus.COMPLETED


async def test_knowledge_graph_integration(runtime):
    runtime.knowledge.add("Runtime", "wires", "EventBus")
    runtime.knowledge.add("Runtime", "wires", "MemoryEngine")
    assert runtime.knowledge.size == 2
    assert len(runtime.knowledge.query(subject="Runtime")) == 2
    assert runtime.health()["knowledge_triples"] == 2


async def test_agents_emit_events(runtime):
    seen: list[str] = []

    async def h(e):
        seen.append(e.type)

    runtime.bus.subscribe("agent.started", h)
    await runtime.run_goal("ping")
    assert "agent.started" in seen
