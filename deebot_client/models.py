"""Models module."""
import os
from dataclasses import dataclass
from enum import IntEnum, unique

from aiohttp import ClientSession

from deebot_client.const import DataType


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
    def nick(self) -> str | None:
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

    @property
    def data_type(self) -> DataType:
        """Return data type."""
        return DataType.JSON


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
        if os.path.exists(str(value)):
            # User could provide a path to a CA Cert as well, which is useful for Bumper
            if os.path.isfile(str(value)):
                return value
            raise ValueError(f"Certificate path provided is not a file: {value}")

    raise ValueError(f'Cannot convert "{value}" to a bool or certificate path')


class Configuration:
    """Configuration representation."""

    def __init__(
        self,
        session: ClientSession,
        *,
        device_id: str,
        country: str,
        continent: str,
        verify_ssl: bool | str = True,
    ):
        self._session = session
        self._device_id = device_id
        self._country = country
        self._continent = continent
        self._verify_ssl = _str_to_bool_or_cert(verify_ssl)

    @property
    def session(self) -> ClientSession:
        """Client session."""
        return self._session

    @property
    def device_id(self) -> str:
        """Device id."""
        return self._device_id

    @property
    def country(self) -> str:
        """Country code."""
        return self._country

    @property
    def continent(self) -> str:
        """Continent code."""
        return self._continent

    @property
    def verify_ssl(self) -> bool | str:
        """Return bool or path to cert."""
        return self._verify_ssl
