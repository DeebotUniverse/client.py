from __future__ import annotations

import asyncio
from typing import Any

from deebot_client.util import OnChangedDict, cancel, create_task


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


def test_on_changed_dict() -> None:
    callback_count = 0

    def increase_counter() -> None:
        nonlocal callback_count
        callback_count += 1

    sut: OnChangedDict[str, int] = OnChangedDict(increase_counter)

    sut["test"] = 1001
    assert callback_count == 1
    assert sut["test"] == 1001

    sut.update({"test": 1002, "test2": 2001, "test3": 3001, "test4": 4001})
    assert sut["test"] == 1002
    assert callback_count == 2

    del sut["test"]
    assert "test" not in sut
    assert callback_count == 3

    assert sut.pop("test2") == 2001
    assert "test2" not in sut
    assert callback_count == 4

    (popped_key, popped_value) = sut.popitem()
    assert popped_key == "test4"
    assert popped_value == 4001
    assert "test4" not in sut
    assert callback_count == 5

    sut.clear()
    assert sut == {}
    assert callback_count == 6
