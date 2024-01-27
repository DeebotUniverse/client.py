"""Test models."""
from __future__ import annotations

import ssl
from typing import TYPE_CHECKING

import pytest

from deebot_client.configuration import create_config
from deebot_client.exceptions import DeebotError

if TYPE_CHECKING:
    from aiohttp import ClientSession


@pytest.mark.parametrize(
    (
        "country",
        "override_mqtt_url",
        "expected_hostname",
        "expected_port",
        "expect_ssl_context",
    ),
    [
        ("CN", None, "mq.ecouser.net", 443, True),
        ("CN", "mqtt://localhost", "localhost", 1883, False),
        ("CN", "mqtts://localhost", "localhost", 8883, True),
        ("IT", None, "mq-eu.ecouser.net", 443, True),
        ("IT", "mqtt://localhost", "localhost", 1883, False),
        ("IT", "mqtt://localhost:8080", "localhost", 8080, False),
        ("IT", "mqtts://localhost", "localhost", 8883, True),
        ("IT", "mqtts://localhost:443", "localhost", 443, True),
    ],
)
@pytest.mark.parametrize("device_id", ["test", "123"])
def test_config_mqtt(
    session: ClientSession,
    country: str,
    override_mqtt_url: str | None,
    expected_hostname: str,
    expected_port: int,
    device_id: str,
    *,
    expect_ssl_context: bool,
) -> None:
    """Test mqtt part of the configuration."""
    config = create_config(
        session=session,
        device_id=device_id,
        country=country,
        override_mqtt_url=override_mqtt_url,
    )
    mqtt = config.mqtt
    assert mqtt.hostname == expected_hostname
    assert mqtt.device_id == device_id
    assert mqtt.port == expected_port
    if expect_ssl_context:
        assert isinstance(mqtt.ssl_context, ssl.SSLContext)
    else:
        assert mqtt.ssl_context is None


@pytest.mark.parametrize(
    ("override_mqtt_url", "error_msg"),
    [
        ("http://test", "Invalid scheme. Expecting mqtt or mqtts"),
        ("mqtt://:80", "Hostame is required"),
        ("mqtt://", "Hostame is required"),
    ],
)
def test_config_override_mqtt_url_invalid(
    session: ClientSession, override_mqtt_url: str, error_msg: str
) -> None:
    """Test that an invalid mqtt override url will raise a DeebotError."""
    with pytest.raises(DeebotError, match=error_msg):
        create_config(
            session=session,
            device_id="123",
            country="IT",
            override_mqtt_url=override_mqtt_url,
        )


def test_config_override_rest_url(
    session: ClientSession,
) -> None:
    """Test overriding the rest url in the configuration."""
    url = "https://test.example.com"
    config = create_config(
        session=session,
        device_id="123",
        country="IT",
        override_rest_url=url,
    )
    assert config.rest.portal_url == url
    assert config.rest.login_url == url
    assert config.rest.auth_code_url == url
