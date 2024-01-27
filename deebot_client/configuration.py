"""Deebot configuration."""
from __future__ import annotations

from dataclasses import dataclass
import ssl
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from deebot_client.const import COUNTRY_CHINA
from deebot_client.exceptions import DeebotError
from deebot_client.util.continents import get_continent_url_postfix

if TYPE_CHECKING:
    from aiohttp import ClientSession


@dataclass(frozen=True, kw_only=True)
class MqttConfiguration:
    """Mqtt configuration."""

    hostname: str
    port: int
    ssl_context: ssl.SSLContext | None
    device_id: str


@dataclass(frozen=True, kw_only=True)
class RestConfiguration:
    """Rest configuration."""

    session: ClientSession
    device_id: str
    country: str
    portal_url: str
    login_url: str
    auth_code_url: str


@dataclass(frozen=True)
class Configuration:
    """Configuration representation."""

    rest: RestConfiguration
    mqtt: MqttConfiguration


def create_config(
    session: ClientSession,
    device_id: str,
    country: str,
    *,
    override_mqtt_url: str | None = None,
    override_rest_url: str | None = None,
) -> Configuration:
    """Create configuration."""
    continent_postfix = get_continent_url_postfix(country)
    if override_rest_url:
        portal_url = login_url = auth_code_url = override_rest_url
    else:
        portal_url = f"https://portal{continent_postfix}.ecouser.net/"
        tld = country = country.lower()
        if country != COUNTRY_CHINA:
            tld = "com"
        login_url = f"https://gl-{country}-api.ecovacs.{tld}"
        auth_code_url = f"https://gl-{country}-openapi.ecovacs.{tld}"

    rest_config = RestConfiguration(
        session=session,
        device_id=device_id,
        country=country,
        portal_url=portal_url,
        login_url=login_url,
        auth_code_url=auth_code_url,
    )

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

    mqtt_config = MqttConfiguration(
        hostname=hostname,
        port=port,
        ssl_context=ssl_ctx,
        device_id=device_id,
    )

    return Configuration(rest_config, mqtt_config)
