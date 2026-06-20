from genesis.orchestrator.loop import DEFAULT_PHASES, Phase


async def test_full_loop_runs_all_phases(runtime):
    result = await runtime.run_goal("Build a URL shortener")
    # Non-optional phases must all appear.
    required = [p.name for p in DEFAULT_PHASES if not p.optional]
    produced = [p.phase for p in result.phases]
    for name in required:
        assert name in produced
    assert result.reflection is not None
    assert result.run_id


async def test_loop_persists_episodic_memory(runtime):
    before = runtime.memory.long_term_count
    await runtime.run_goal("Write a haiku about engineering")
    after = runtime.memory.long_term_count
    # one memory per phase + one reflection
    assert after > before


async def test_custom_phase_list_is_respected(runtime):
    phases = [Phase(name="plan", agent_role="planner")]
    result = await runtime.run_goal("Tiny goal", phases=phases)
    assert [p.phase for p in result.phases] == ["plan"]


async def test_reflection_is_recalled_next_run(runtime):
    await runtime.run_goal("Improve caching strategy")
    lessons = runtime.reflection.past_lessons("caching", k=5)
    assert lessons  # a reflection was stored and is retrievable
