from genesis.core.event_bus import EventBus
from genesis.core.task_queue import Task, TaskQueue, TaskStatus


async def test_submit_and_claim_fifo():
    q = TaskQueue(EventBus())
    await q.submit(Task(goal="first"))
    await q.submit(Task(goal="second"))
    a = await q.claim()
    b = await q.claim()
    assert (a.goal, b.goal) == ("first", "second")
    assert a.status is TaskStatus.RUNNING


async def test_priority_ordering():
    q = TaskQueue(EventBus())
    await q.submit(Task(goal="low", priority=0))
    await q.submit(Task(goal="high", priority=10))
    first = await q.claim()
    assert first.goal == "high"


async def test_complete_and_fail():
    q = TaskQueue(EventBus())
    t = await q.submit(Task(goal="x"))
    await q.claim()
    done = await q.complete(t.id, {"ok": True})
    assert done.status is TaskStatus.COMPLETED
    assert done.result == {"ok": True}

    t2 = await q.submit(Task(goal="y"))
    await q.claim()
    failed = await q.fail(t2.id, "boom")
    assert failed.status is TaskStatus.FAILED
    assert failed.error == "boom"
