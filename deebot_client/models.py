"""Models module."""
from dataclasses import dataclass
from enum import IntEnum, unique
from typing import Optional


class DeviceInfo(dict):
    """Class holds all values, which we get from api. Common values can be accessed through properties."""

    @property
    def company(self) -> str:
        """Return company."""
        return str(self["company"])

    @property
    def did(self) -> str:
        """Return did."""
        return str(self["did"])

    @property
    def name(self) -> str:
        """Return name."""
        return str(self["name"])

    @property
    def nick(self) -> Optional[str]:
        """Return nick name."""
        return self.get("nick", None)

    @property
    def resource(self) -> str:
        """Return resource."""
        return str(self["resource"])

    @property
    def device_name(self) -> str:
        """Return device name."""
        return str(self["deviceName"])

    @property
    def status(self) -> int:
        """Return device status."""
        return int(self["status"])

    @property
    def get_class(self) -> str:
        """Return device class."""
        return str(self["class"])


@dataclass(frozen=True)
class Room:
    """Room representation."""

    name: str
    id: int
    coordinates: str


@unique
class VacuumState(IntEnum):
    """Vacuum state representation."""

    IDLE = 1
    CLEANING = 2
    RETURNING = 3
    DOCKED = 4
    ERROR = 5
    PAUSED = 6


@dataclass(frozen=True)
class Credentials:
    """Credentials representation."""

    token: str
    user_id: str
    expires_at: int = 0
