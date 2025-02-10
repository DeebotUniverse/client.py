"""Models module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum, unique
from pathlib import Path
from typing import TYPE_CHECKING, Required, Self, TypedDict

if TYPE_CHECKING:
    from deebot_client.capabilities import Capabilities
    from deebot_client.const import DataType

ApiDeviceInfo = TypedDict(
    "ApiDeviceInfo",
    {
        "class": Required[str],
        "company": Required[str],
        "deviceName": str,
        "did": Required[str],
        "name": Required[str],
        "nick": str,
        "resource": Required[str],
    },
    total=False,
)


@dataclass(frozen=True)
class StaticDeviceInfo:
    """Static device info."""

    data_type: DataType
    capabilities: Capabilities


@dataclass(frozen=True)
class DeviceInfo:
    """Device info."""

    api: ApiDeviceInfo
    static: StaticDeviceInfo


@dataclass(frozen=True)
class Room:
    """Room representation."""

    name: str
    id: int
    coordinates: str


@unique
class State(IntEnum):
    """State representation."""

    IDLE = 1
    CLEANING = 2
    RETURNING = 3
    DOCKED = 4
    ERROR = 5
    PAUSED = 6


@unique
class CleanAction(StrEnum):
    """Enum class for all possible clean actions."""

    xml_value: str

    def __new__(cls, value: str, xml_value: str = "") -> Self:
        """New CleanAction."""
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.xml_value = xml_value
        return obj

    @classmethod
    def from_xml(cls, value: str) -> CleanAction:
        """Get CleanAction from xml value."""
        for clean_action in CleanAction:
            if clean_action.xml_value == value:
                return clean_action

        msg = f"{value} is not a valid {cls.__name__}"
        raise ValueError(msg)

    START = "start", "s"
    PAUSE = "pause", "p"
    RESUME = "resume", "r"
    STOP = "stop", "h"


@unique
class CleanMode(StrEnum):
    """Enum class for all possible clean modes."""

    xml_value: str

    def __new__(cls, value: str, xml_value: str = "") -> Self:
        """New CleanMode."""
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.xml_value = xml_value
        return obj

    @classmethod
    def from_xml(cls, value: str) -> CleanMode:
        """Get CleanMode from xml value."""
        for clean_mode in CleanMode:
            if clean_mode.xml_value == value:
                return clean_mode

        msg = f"{value} is not a valid {cls.__name__}"
        raise ValueError(msg)

    AUTO = "auto", "auto"
    SPOT_AREA = "spotArea", "SpotArea"
    CUSTOM_AREA = "customArea", "spot"


@dataclass(frozen=True)
class Credentials:
    """Credentials representation."""

    token: str
    user_id: str
    expires_at: int = 0


def _str_to_bool_or_cert(value: bool | str) -> bool | str:
    """Convert string to bool or certificate."""
    if isinstance(value, bool):
        return value

    if value is not None:
        value = value.lower()
        if value in ("y", "yes", "t", "true", "on", "1"):
            return True
        if value in ("n", "no", "f", "false", "off", "0"):
            return False
        path = Path(str(value))
        if path.exists():
            # User could provide a path to a CA Cert as well, which is useful for Bumper
            if path.is_file():
                return value
            msg = f"Certificate path provided is not a file: {value}"
            raise ValueError(msg)

    msg = f'Cannot convert "{value}" to a bool or certificate path'
    raise ValueError(msg)
