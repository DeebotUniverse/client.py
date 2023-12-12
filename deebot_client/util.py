"""Util module."""
from __future__ import annotations

import asyncio
import base64
from contextlib import suppress
from enum import IntEnum, unique
import hashlib
import lzma
from typing import TYPE_CHECKING, Any, Self, TypeVar

from .logging_filter import get_logger

_LOGGER = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Iterable, Mapping

_T = TypeVar("_T")


def md5(text: str) -> str:
    """Hash text using md5."""
    return hashlib.md5(bytes(str(text), "utf8")).hexdigest()  # noqa: S324


def decompress_7z_base64_data(data: str) -> bytes:
    """Decomporess base64 decoded 7z compressed string."""
    _LOGGER.debug("[decompress7zBase64Data] Begin")
    final_array = bytearray()

    # Decode Base64
    decoded = base64.b64decode(data)

    i = 0
    for idx in decoded:
        if i == 8:
            final_array += b"\x00\x00\x00\x00"
        final_array.append(idx)
        i += 1

    dec = lzma.LZMADecompressor(lzma.FORMAT_AUTO, None, None)
    decompressed_data = dec.decompress(final_array)

    _LOGGER.debug("[decompress7zBase64Data] Done")
    return decompressed_data


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

    def __new__(cls, *args: int, **_: Mapping[Any, Any]) -> Self:
        """Create new DisplayNameIntEnum."""
        obj = int.__new__(cls)
        obj._value_ = args[0]
        return obj

    def __init__(self, value: int, display_name: str | None = None) -> None:
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
    def get(cls, value: str) -> Self:
        """Get enum member from name or display_name."""
        value = str(value).upper()
        if value in cls.__members__:
            return cls[value]

        for member in cls:
            if value == member.display_name.upper():
                return member

        msg = f"'{value}' is not a valid {cls.__name__} member"
        raise ValueError(msg)

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

    _MODIFING_FUNCTIONS = (
        "append",
        "clear",
        "extend",
        "insert",
        "pop",
        "remove",
        "__setitem__",
        "__delitem__",
        "__add__",
    )

    def __init__(
        self, on_change: Callable[[], None], iterable: Iterable[_T] = ()
    ) -> None:
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

    _MODIFING_FUNCTIONS = (
        "clear",
        "pop",
        "popitem",
        "update",
        "__setitem__",
        "__delitem__",
    )

    def __init__(
        self, on_change: Callable[[], None], iterable: Iterable[tuple[_KT, _VT]] = ()
    ) -> None:
        super().__init__(iterable)
        self._on_change = on_change

    def __getattribute__(self, __name: str) -> Any:
        if __name in OnChangedDict._MODIFING_FUNCTIONS:
            self._on_change()
        return super().__getattribute__(__name)


LST = list[_T] | set[_T] | tuple[_T, ...]


def short_name(value: str) -> str:
    """Return value after last dot."""
    return value.rsplit(".", maxsplit=1)[-1]
