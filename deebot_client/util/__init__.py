"""Util module."""

from __future__ import annotations

import asyncio
import base64
from contextlib import suppress
from enum import Enum
import hashlib
import lzma
from typing import TYPE_CHECKING, Any, TypeVar

from deebot_client.logging_filter import get_logger

_LOGGER = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Iterable

_T = TypeVar("_T")


def md5(text: str) -> str:
    """Hash text using md5."""
    return hashlib.md5(bytes(str(text), "utf8")).hexdigest()  # noqa: S324


def decompress_7z_base64_data(data: str) -> bytes:
    """Decompress base64 decoded 7z compressed string."""
    final_array = bytearray()

    # Decode Base64
    decoded = base64.b64decode(data)

    for i, idx in enumerate(decoded):
        if i == 8:
            final_array.extend(b"\x00\x00\x00\x00")
        final_array.append(idx)

    dec = lzma.LZMADecompressor(lzma.FORMAT_AUTO, None, None)
    return dec.decompress(final_array)


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


class OnChangedList(list[_T]):
    """List, which will call passed on_change if a change happens."""

    _MODIFYING_FUNCTIONS = (
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

    def __getattribute__(self, name: str, /) -> Any:
        if name in OnChangedList._MODIFYING_FUNCTIONS:
            self._on_change()
        return super().__getattribute__(name)


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class OnChangedDict(dict[_KT, _VT]):
    """Dict, which will call passed on_change if a change happens."""

    _MODIFYING_FUNCTIONS = (
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

    def __getattribute__(self, name: str, /) -> Any:
        if name in OnChangedDict._MODIFYING_FUNCTIONS:
            self._on_change()
        return super().__getattribute__(name)


LST = list[_T] | set[_T] | tuple[_T, ...]


def short_name(value: str) -> str:
    """Return value after last dot."""
    return value.rsplit(".", maxsplit=1)[-1]
