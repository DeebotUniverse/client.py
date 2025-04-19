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
    class OnChangedListener:
        def __init__(self) -> None:
            self.__counter = 0

        def on_changed_dict(self) -> None:
            self.__counter += 1

        def counter(self) -> int:
            return self.__counter

    listener = OnChangedListener()

    sut: OnChangedDict[str, int] = OnChangedDict(listener.on_changed_dict)

    sut["test"] = 1001  # Should be triggered by __setitem__

    assert sut["test"] == 1001

    sut.update(
        {"test": 1002, "test2": 2001, "test3": 3001, "test4": 4001}
    )  # Should trigger update()

    assert sut["test"] == 1002

    del sut["test"]  # Should trigger __delitem__

    assert "test" not in sut

    assert sut.pop("test2") == 2001  # Should trigger pop()

    (popped_key, popped_value) = sut.popitem()  # Should trigger popitem()
    assert popped_key == "test4"
    assert popped_value == 4001

    sut.clear()  # Should trigger clear

    assert listener.counter() == 6
