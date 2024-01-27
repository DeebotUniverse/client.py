from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

import aiohttp
from aiomqtt import Client
import pytest

from deebot_client.api_client import ApiClient
from deebot_client.authentication import Authenticator
from deebot_client.configuration import (
    Configuration,
    MqttConfiguration,
    RestConfiguration,
    create_config,
)
from deebot_client.event_bus import EventBus
from deebot_client.hardware.deebot import FALLBACK, get_static_device_info
from deebot_client.models import (
    Credentials,
    DeviceInfo,
    StaticDeviceInfo,
)
from deebot_client.mqtt_client import MqttClient

from .fixtures.mqtt_server import MqttServer

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator


@pytest.fixture
async def session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    async with aiohttp.ClientSession() as client_session:
        logging.basicConfig(level=logging.DEBUG)
        yield client_session


@pytest.fixture
def config(session: aiohttp.ClientSession) -> Configuration:
    return create_config(
        session=session,
        device_id="Test_device",
        country="IT",
    )


@pytest.fixture
def rest_config(config: Configuration) -> RestConfiguration:
    return config.rest


@pytest.fixture
def authenticator() -> Authenticator:
    authenticator = Mock(spec_set=Authenticator)
    authenticator.authenticate.return_value = Credentials("token", "user_id", 9999)
    authenticator.post_authenticated.return_value = {
        "header": {
            "pri": 1,
            "tzm": 480,
            "ts": "1304623069888",
            "ver": "0.0.1",
            "fwVer": "1.8.2",
            "hwVer": "0.1.1",
        },
        "body": {
            "code": 500,
            "msg": "fail",
        },
    }
    return authenticator


@pytest.fixture
def api_client(authenticator: Authenticator) -> ApiClient:
    return ApiClient(authenticator)


@pytest.fixture(scope="session")
def mqtt_server() -> Generator[MqttServer, None, None]:
    server = MqttServer()
    server.run()
    yield server
    server.stop()


@pytest.fixture
def mqtt_config(config: Configuration, mqtt_server: MqttServer) -> MqttConfiguration:
    new_config = create_config(
        session=config.rest.session,
        device_id=config.rest.device_id,
        country=config.rest.country,
        override_mqtt_url=f"mqtt://localhost:{mqtt_server.get_port()}",
    )
    return new_config.mqtt


@pytest.fixture
async def mqtt_client(
    authenticator: Authenticator,
    mqtt_config: MqttConfiguration,
) -> AsyncGenerator[MqttClient, None]:
    client = MqttClient(mqtt_config, authenticator)
    yield client
    await client.disconnect()


@pytest.fixture
async def test_mqtt_client(
    mqtt_config: MqttConfiguration,
) -> AsyncGenerator[Client, None]:
    async with Client(
        hostname=mqtt_config.hostname,
        port=mqtt_config.port,
        identifier="Test-helper",
        tls_context=mqtt_config.ssl_context,
    ) as client:
        yield client


@pytest.fixture
def static_device_info() -> StaticDeviceInfo:
    return get_static_device_info(FALLBACK)


@pytest.fixture
def device_info(static_device_info: StaticDeviceInfo) -> DeviceInfo:
    return DeviceInfo(
        {
            "company": "company",
            "did": "did",
            "name": "name",
            "nick": "nick",
            "resource": "resource",
            "deviceName": "device_name",
            "status": 1,
            "class": "get_class",
        },
        static_device_info,
    )


@pytest.fixture
def execute_mock() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def event_bus(execute_mock: AsyncMock, device_info: DeviceInfo) -> EventBus:
    return EventBus(execute_mock, device_info.capabilities.get_refresh_commands)


@pytest.fixture
def event_bus_mock(event_bus: EventBus) -> Mock:
    return Mock(spec_set=EventBus, wraps=event_bus)


@pytest.fixture(name="caplog")
def caplog_fixture(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    """Set log level to debug for tests using the caplog fixture."""
    caplog.set_level(logging.DEBUG)
    return caplog
