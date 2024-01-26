from __future__ import annotations

import asyncio
from typing import Any

from deebot_client.util import cancel, create_task


async def test_create_task_and_cancel() -> None:
    async def sleep(delay: float) -> None:
        await asyncio.sleep(delay)

    tasks: set[asyncio.Future[Any]] = set()

    task = create_task(tasks, sleep(0.2))
    # verify task was added to tasks
    assert len(tasks) == 1
    assert not task.done()

    await asyncio.sleep(0.3)
    # verify done callback removed task again
    assert len(tasks) == 0
    assert not task.cancelled()
    assert task.done()

    _tasks = [create_task(tasks, sleep(1)), create_task(tasks, sleep(1))]
    assert len(tasks) == 2
    for task in _tasks:
        assert not task.done()

    # cancel all tasks and verify that they are cancelled
    await cancel(tasks)

    assert len(tasks) == 0
    for task in _tasks:
        assert task.cancelled()
        assert task.done()
