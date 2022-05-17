"""Configuration module."""
import os
from dataclasses import dataclass
from typing import Union

from aiohttp import ClientSession


def _str_to_bool_or_cert(value: Union[bool, str]) -> Union[bool, str]:
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


class AuthenticationConfig:
    """Authentication configuration."""

    def __init__(
        self,
        session: ClientSession,
        *,
        device_id: str,
        country: str,
        continent: str,
        verify_ssl: Union[bool, str] = True,
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
    def verify_ssl(self) -> Union[bool, str]:
        """Return bool or path to cert."""
        return self._verify_ssl


@dataclass(frozen=True)
class MapConfig:
    """Map config."""

    crop_on_outermost_subsets: bool = False


@dataclass(frozen=True)
class Config:
    """Configuration."""

    map: MapConfig = MapConfig()
