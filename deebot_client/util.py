"""Util module."""
import hashlib
from enum import IntEnum, unique
from typing import Callable, Iterable, Mapping, Optional, TypeVar, Union, overload

from typing_extensions import SupportsIndex


def md5(text: str) -> str:
    """Hash text using md5."""
    return hashlib.md5(bytes(str(text), "utf8")).hexdigest()


@unique
class DisplayNameIntEnum(IntEnum):
    """Int enum with a property "display_name"."""

    def __new__(cls, *args: tuple, **_: Mapping) -> "DisplayNameIntEnum":
        """Create new DisplayNameIntEnum."""
        obj = int.__new__(cls)
        obj._value_ = args[0]
        return obj

    def __init__(self, value: int, display_name: Optional[str] = None):
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
    def get(cls, value: str) -> "DisplayNameIntEnum":
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


_T = TypeVar("_T")


class OnChangedList(list[_T]):
    """List, which will call passed on_change if a change happens."""

    def __init__(self, on_change: Callable[[], None], iterable: Iterable[_T] = ()):
        super().__init__(iterable)
        self._on_change = on_change

    def append(self, __object: _T) -> None:
        """Append object to the end of the list."""

        self._on_change()
        super().append(__object)

    def clear(self) -> None:
        """Remove all items from list."""

        self._on_change()
        super().clear()

    def extend(self, __iterable: Iterable[_T]) -> None:
        """Extend list by appending elements from the iterable."""

        self._on_change()
        super().extend(__iterable)

    def insert(self, __index: SupportsIndex, __object: _T) -> None:
        """Insert object before index."""

        self._on_change()
        super().insert(__index, __object)

    def pop(self, __index=...) -> _T:  # type: ignore
        """
        Remove and return item at index (default last).

        Raises IndexError if list is empty or index is out of range.
        """

        self._on_change()
        return super().pop(__index)

    def remove(self, __value: _T) -> None:
        """
        Remove first occurrence of value.

        Raises ValueError if the value is not present.
        """

        self._on_change()
        super().remove(__value)

    @overload
    def __setitem__(self, i: SupportsIndex, o: _T) -> None:
        ...

    @overload
    def __setitem__(self, s: slice, o: Iterable[_T]) -> None:
        ...

    def __setitem__(self, i, o) -> None:  # type: ignore
        self._on_change()
        super().__setitem__(i, o)

    def __delitem__(self, i: Union[SupportsIndex, slice]) -> None:
        self._on_change()
        super().__delitem__(i)

    def __add__(self, x: list[_T]) -> list[_T]:
        self._on_change()
        return super().__add__(x)


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class OnChangedDict(dict[_KT, _VT]):
    """Dict, which will call passed on_change if a change happens."""

    def __init__(
        self, on_change: Callable[[], None], iterable: Iterable[tuple[_KT, _VT]] = ()
    ):
        super().__init__(iterable)
        self._on_change = on_change

    def clear(self) -> None:
        """Remove all items."""

        self._on_change()
        super().clear()

    @overload
    def pop(self, key: _KT) -> _VT:
        ...

    @overload
    def pop(self, key: _KT, default: Union[_VT, _T] = ...) -> Union[_VT, _T]:
        ...

    def pop(self, key, default=...):  # type: ignore
        """
        Remove specified key and return the corresponding value.

        If the key is not found, return the default if given; otherwise,
        raise a KeyError.
        """

        self._on_change()
        return super().pop(key, default)

    def popitem(self) -> tuple[_KT, _VT]:
        """
        Remove and return a (key, value) pair as a 2-tuple.

        Pairs are returned in LIFO (last-in, first-out) order.
        Raises KeyError if the dict is empty.
        """
        self._on_change()
        return super().popitem()

    @overload
    def update(self, __m: Mapping[_KT, _VT], **kwargs: _VT) -> None:
        ...

    @overload
    def update(self, __m: Iterable[tuple[_KT, _VT]], **kwargs: _VT) -> None:
        ...

    @overload
    def update(self, **kwargs: _VT) -> None:
        ...

    def update(self, __m, **kwargs) -> None:  # type: ignore
        """Update dict."""
        self._on_change()
        super().update(__m, **kwargs)

    def __setitem__(self, k: _KT, v: _VT) -> None:
        self._on_change()
        super().__setitem__(k, v)

    def __delitem__(self, v: _KT) -> None:
        self._on_change()
        super().__delitem__(v)
