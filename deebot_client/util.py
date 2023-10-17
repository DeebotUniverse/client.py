"""Util module."""
from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable, Coroutine, Iterable, Mapping
from contextlib import suppress
from enum import IntEnum, unique
from typing import Any, TypeVar

_T = TypeVar("_T")


def md5(text: str) -> str:
    """Hash text using md5."""
    return hashlib.md5(bytes(str(text), "utf8")).hexdigest()


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


@unique
class DisplayNameIntEnum(IntEnum):
    """Int enum with a property "display_name"."""

    def __new__(cls, *args: int, **_: Mapping[Any, Any]) -> DisplayNameIntEnum:
        """Create new DisplayNameIntEnum."""
        obj = int.__new__(cls)
        obj._value_ = args[0]
        return obj

    def __init__(self, value: int, display_name: str | None = None):
        super().__init__()
        self._value_ = value
        self._display_name = display_name

    @property
    def display_name(self) -> str:
        """Return the custom display name or the lowered name property."""
        if self._display_name:
            return self._display_name

        return self.name.lower()

    @classmethod
    def get(cls, value: str) -> DisplayNameIntEnum:
        """Get enum member from name or display_name."""
        value = str(value).upper()
        if value in cls.__members__:
            return cls[value]

        for member in cls:
            if value == member.display_name.upper():
                return member

        raise ValueError(f"'{value}' is not a valid {cls.__name__} member")

    def __eq__(self, x: object) -> bool:
        if not isinstance(x, type(self)):
            return False
        return bool(self._value_ == x._value_)

    def __ne__(self, x: object) -> bool:
        return not self.__eq__(x)

    def __hash__(self) -> int:
        return hash(self._value_)


class OnChangedList(list[_T]):
    """List, which will call passed on_change if a change happens."""

    _MODIFING_FUNCTIONS = [
        "append",
        "clear",
        "extend",
        "insert",
        "pop",
        "remove",
        "__setitem__",
        "__delitem__",
        "__add__",
    ]

    def __init__(self, on_change: Callable[[], None], iterable: Iterable[_T] = ()):
        super().__init__(iterable)
        self._on_change = on_change

    def __getattribute__(self, __name: str) -> Any:
        if __name in OnChangedList._MODIFING_FUNCTIONS:
            self._on_change()
        return super().__getattribute__(__name)


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class OnChangedDict(dict[_KT, _VT]):
    """Dict, which will call passed on_change if a change happens."""

    _MODIFING_FUNCTIONS = [
        "clear",
        "pop",
        "popitem",
        "update",
        "__setitem__",
        "__delitem__",
    ]

    def __init__(
        self, on_change: Callable[[], None], iterable: Iterable[tuple[_KT, _VT]] = ()
    ):
        super().__init__(iterable)
        self._on_change = on_change

    def __getattribute__(self, __name: str) -> Any:
        if __name in OnChangedDict._MODIFING_FUNCTIONS:
            self._on_change()
        return super().__getattribute__(__name)


LST = list[_T] | set[_T] | tuple[_T, ...]
