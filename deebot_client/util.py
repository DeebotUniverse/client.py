"""Util module."""
import copy
import hashlib
from enum import IntEnum, unique
from typing import Mapping, Optional, Set, Tuple


def md5(text: str) -> str:
    """Hash text using md5."""
    return hashlib.md5(bytes(str(text), "utf8")).hexdigest()


# all lowercase
_SANITIZE_LOG_KEYS: Set[str] = {
    "auth",
    "token",
    "id",
    "login",
    "mobile",
    "user",
    "email",
}


def sanitize_data(data: dict) -> dict:
    """Sanitize data (remove personal data)."""
    sanitized_data = copy.deepcopy(data)
    for key in sanitized_data.keys():
        if any(substring in key.lower() for substring in _SANITIZE_LOG_KEYS):
            sanitized_data[key] = "[REMOVED]"

    return sanitized_data


@unique
class DisplayNameIntEnum(IntEnum):
    """Int enum with a property "display_name"."""

    def __new__(cls, *args: Tuple, **_: Mapping) -> "DisplayNameIntEnum":
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
