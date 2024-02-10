# The functions in this files are copied from Home Assistant
# See https://github.com/home-assistant/core/blob/8b1cfbc46cc79e676f75dfa4da097a2e47375b6f/homeassistant/core.py#L715


# How long to wait to log tasks that are blocking
from __future__ import annotations

import asyncio
from logging import getLogger
from time import monotonic
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Collection

_LOGGER = getLogger(__name__)


BLOCK_LOG_TIMEOUT = 1


def _cancelling(task: asyncio.Future[Any]) -> bool:
    """Return True if task is cancelling."""
    return bool((cancelling_ := getattr(task, "cancelling", None)) and cancelling_())


async def _await_and_log_pending(pending: Collection[asyncio.Future[Any]]) -> None:
    """Await and log tasks that take a long time."""
    wait_time = 0
    while pending:
        _, pending = await asyncio.wait(pending, timeout=BLOCK_LOG_TIMEOUT)
        if not pending:
            return
        wait_time += BLOCK_LOG_TIMEOUT
        for task in pending:
            _LOGGER.debug("Waited %s seconds for task: %s", wait_time, task)


async def block_till_done(tasks: set[asyncio.Future[Any]]) -> None:
    """Block until all pending work is done."""
    # To flush out any call_soon_threadsafe
    await asyncio.sleep(0)
    start_time: float | None = None
    current_task = asyncio.current_task()

    while tasks_ := [
        task for task in tasks if task is not current_task and not _cancelling(task)
    ]:
        await _await_and_log_pending(tasks_)

        if start_time is None:
            # Avoid calling monotonic() until we know
            # we may need to start logging blocked tasks.
            start_time = 0
        elif start_time == 0:
            # If we have waited twice then we set the start
            # time
            start_time = monotonic()
        elif monotonic() - start_time > BLOCK_LOG_TIMEOUT:
            # We have waited at least three loops and new tasks
            # continue to block. At this point we start
            # logging all waiting tasks.
            for task in tasks_:
                _LOGGER.debug("Waiting for task: %s", task)
