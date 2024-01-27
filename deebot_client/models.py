"""Models module."""
from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import IntEnum, StrEnum, unique
from pathlib import Path
import ssl
from typing import TYPE_CHECKING, Required, TypedDict
from urllib.parse import urlparse

from deebot_client.const import COUNTRY_CHINA
from deebot_client.exceptions import DeebotError
from deebot_client.util.continents import get_continent_url_postfix

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from deebot_client.capabilities import Capabilities
    from deebot_client.const import DataType


ApiDeviceInfo = TypedDict(
    "ApiDeviceInfo",
    {
        "company": Required[str],
        "did": Required[str],
        "name": Required[str],
        "nick": str,
        "resource": Required[str],
        "deviceName": str,
        "status": int,
        "class": Required[str],
    },
    total=False,
)


@dataclass(frozen=True)
class StaticDeviceInfo:
    """Static device info."""

    data_type: DataType
    capabilities: Capabilities


class DeviceInfo:
    """Device info."""

    def __init__(
        self, api_device_info: ApiDeviceInfo, static_device_info: StaticDeviceInfo
    ) -> None:
        self._api_device_info = api_device_info
        self._static_device_info = static_device_info

    @property
    def api_device_info(self) -> ApiDeviceInfo:
        """Return all data goten from the api."""
        return self._api_device_info

    @property
    def company(self) -> str:
        """Return company."""
        return self._api_device_info["company"]

    @property
    def did(self) -> str:
        """Return did."""
        return str(self._api_device_info["did"])

    @property
    def name(self) -> str:
        """Return name."""
        return str(self._api_device_info["name"])

    @property
    def nick(self) -> str | None:
        """Return nick name."""
        return self._api_device_info.get("nick", None)

    @property
    def resource(self) -> str:
        """Return resource."""
        return str(self._api_device_info["resource"])

    @property
    def get_class(self) -> str:
        """Return device class."""
        return str(self._api_device_info["class"])

    @property
    def data_type(self) -> DataType:
        """Return data type."""
        return self._static_device_info.data_type

    @property
    def capabilities(self) -> Capabilities:
        """Return capabilities."""
        return self._static_device_info.capabilities


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

    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"


@unique
class CleanMode(StrEnum):
    """Enum class for all possible clean modes."""

    AUTO = "auto"
    SPOT_AREA = "spotArea"
    CUSTOM_AREA = "customArea"


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


@dataclass(frozen=True, kw_only=True)
class MqttConfiguration:
    """Mqtt configuration."""

    hostname: str
    port: int
    ssl_context: ssl.SSLContext | None
    device_id: str


@dataclass(frozen=True, kw_only=True)
class Configuration:
    """Configuration representation."""

    session: ClientSession
    device_id: str
    country: str

    portal_url: str = field(init=False)
    login_url: str = field(init=False)
    authcode_url: str = field(init=False)
    mqtt: MqttConfiguration = field(init=False)
    override_mqtt_url: InitVar[str | None] = None
    override_portal_url: InitVar[str | None] = None

    def __post_init__(
        self, override_mqtt_url: str | None, override_rest_url: str | None
    ) -> None:
        continent_postfix = get_continent_url_postfix(self.country)
        if override_rest_url:
            portal_url = login_url = authcode_url = override_rest_url
        else:
            portal_url = f"https://portal{continent_postfix}.ecouser.net/"
            tld = country = self.country.lower()
            if self.country != COUNTRY_CHINA:
                tld = "com"
            login_url = f"https://gl-{country}-api.ecovacs.{tld}"
            authcode_url = f"https://gl-{country}-openapi.ecovacs.{tld}"

        object.__setattr__(self, "portal_url", portal_url)
        object.__setattr__(self, "login_url", login_url)
        object.__setattr__(self, "authcode_url", authcode_url)

        if override_mqtt_url:
            url = urlparse(override_mqtt_url)
            match url.scheme:
                case "mqtt":
                    default_port = 1883
                    ssl_ctx = None
                case "mqtts":
                    default_port = 8883
                    ssl_ctx = ssl.create_default_context()
                case _:
                    raise DeebotError("Invalid scheme. Expecting mqtt or mqtts")

            if not url.hostname:
                raise DeebotError("Hostame is required")

            hostname = url.hostname
            port = url.port or default_port
        else:
            hostname = f"mq{continent_postfix}.ecouser.net"
            port = 443
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

        mqtt = MqttConfiguration(
            hostname=hostname,
            port=port,
            ssl_context=ssl_ctx,
            device_id=self.device_id,
        )
        object.__setattr__(self, "mqtt", mqtt)
