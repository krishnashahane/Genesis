from genesis.agents.base import AgentContext


async def test_agent_recalls_memory_in_prompt(runtime):
    # Seed a memory the planner should recall and weave into its prompt.
    await runtime.memory.store("Always rate-limit public endpoints", kind="semantic")
    planner = runtime.agents["planner"]
    msgs = planner.build_messages(
        AgentContext(goal="rate-limit public endpoints", phase="plan")
    )
    user_msg = msgs[-1].content
    assert "rate-limit" in user_msg
    assert "long-term memory" in user_msg.lower()


async def test_agent_act_emits_lifecycle_events(runtime):
    seen: list[str] = []

    async def h(e):
        seen.append(e.type)

    runtime.bus.subscribe("agent.started", h)
    runtime.bus.subscribe("agent.finished", h)
    result = await runtime.agents["coder"].act(
        AgentContext(goal="write a function", phase="build")
    )
    assert result.agent == "coder"
    assert "agent.started" in seen and "agent.finished" in seen


async def test_agent_to_agent_message(runtime):
    seen: list[dict] = []

    async def h(e):
        seen.append(e.payload)

    runtime.bus.subscribe("agent.message", h)
    await runtime.agents["planner"].message("coder", "build step 1")
    assert seen and seen[0]["to"] == "coder"
