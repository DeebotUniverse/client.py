"""Util module."""

from __future__ import annotations

from abc import ABC
import asyncio
from contextlib import suppress
from enum import Enum
import hashlib
from typing import TYPE_CHECKING, Any, TypeVar

from deebot_client.logging_filter import get_logger

_LOGGER = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Iterable

_T = TypeVar("_T")


def md5(text: str) -> str:
    """Hash text using md5."""
    return hashlib.md5(bytes(str(text), "utf8")).hexdigest()  # noqa: S324


def verify_required_class_variables_exists(
    cls: type[Any], required_variables: tuple[str, ...]
) -> None:
    """Verify that the class has the given class variables."""
    if ABC not in cls.__bases__:
        for required in required_variables:
            if not hasattr(cls, required):
                msg = f"Class {cls.__name__} must have a {required} attribute"
                raise ValueError(msg)


def create_task(
    tasks: set[asyncio.Future[Any]], target: Coroutine[Any, Any, _T]
) -> asyncio.Task[_T]:
    """Create task with done callback to remove it from tasks and add it to tasks."""
    task = asyncio.create_task(target)
    tasks.add(task)
    task.add_done_callback(tasks.remove)
    return task


async def cancel(tasks: set[asyncio.Future[Any]]) -> None:
    """Cancel all tasks and wait for their completion."""
    tasks_to_wait = set()
    for task in tasks:
        if task.cancel():
            tasks_to_wait.add(task)

    with suppress(asyncio.CancelledError):
        await asyncio.gather(*tasks_to_wait)


_S = TypeVar("_S", bound=Enum)


def get_enum(enum: type[_S], value: str) -> _S:
    """Get enum member from name."""
    value = value.upper()
    if value in enum.__members__:
        return enum[value]

    msg = f"'{value}' is not a valid {enum.__name__} member"
    raise ValueError(msg)


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class OnChangedDict(dict[_KT, _VT]):
    """Dict, which will call passed on_change if a change happens."""

    _MODIFYING_FUNCTIONS = (
        "clear",
        "pop",
        "popitem",
        "update",
    )

    def __init__(
        self, on_change: Callable[[], None], iterable: Iterable[tuple[_KT, _VT]] = ()
    ) -> None:
        super().__init__(iterable)
        self._on_change = on_change

    # This is needed as __getattribute__ won't be invoked for implicit special method lookup
    def __setitem__(self, key: _KT, value: _VT) -> None:
        self._on_change()
        super().__setitem__(key, value)

    # This is needed as __getattribute__ won't be invoked for implicit special method lookup
    def __delitem__(self, key: _KT) -> None:
        self._on_change()
        return super().__delitem__(key)

    def __getattribute__(self, name: str, /) -> Any:
        if name in OnChangedDict._MODIFYING_FUNCTIONS:
            self._on_change()
        return super().__getattribute__(name)


LST = list[_T] | set[_T] | tuple[_T, ...]


def short_name(value: str) -> str:
    """Return value after last dot."""
    return value.rsplit(".", maxsplit=1)[-1]
