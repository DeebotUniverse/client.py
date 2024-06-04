from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

from aiohttp import ClientSession
from aiomqtt import Client
import pytest

from deebot_client.api_client import ApiClient
from deebot_client.authentication import (
    Authenticator,
    RestConfiguration,
    create_rest_config as create_config_rest,
)
from deebot_client.event_bus import EventBus
from deebot_client.hardware.deebot import FALLBACK, get_static_device_info
from deebot_client.models import (
    ApiDeviceInfo,
    Credentials,
    DeviceInfo,
    StaticDeviceInfo,
)
from deebot_client.mqtt_client import (
    MqttClient,
    MqttConfiguration,
    create_mqtt_config as create_config_mqtt,
)

from .fixtures.mqtt_server import MqttServer

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator


@pytest.fixture
async def session() -> AsyncGenerator[ClientSession, None]:
    async with ClientSession() as client_session:
        logging.basicConfig(level=logging.DEBUG)
        yield client_session


@pytest.fixture
def device_id_and_country() -> tuple[str, str]:
    return ("Test_device", "IT")


@pytest.fixture
def rest_config(
    session: ClientSession, device_id_and_country: tuple[str, str]
) -> RestConfiguration:
    return create_config_rest(
        session=session,
        device_id=device_id_and_country[0],
        alpha_2_country=device_id_and_country[1],
    )


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
def mqtt_config(
    device_id_and_country: tuple[str, str], mqtt_server: MqttServer
) -> MqttConfiguration:
    return create_config_mqtt(
        device_id=device_id_and_country[0],
        country=device_id_and_country[1],
        override_mqtt_url=f"mqtt://localhost:{mqtt_server.get_port()}",
    )


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
async def static_device_info() -> StaticDeviceInfo:
    return await get_static_device_info(FALLBACK)


@pytest.fixture
def api_device_info() -> ApiDeviceInfo:
    return ApiDeviceInfo(
        {
            "company": "company",
            "did": "did",
            "name": "name",
            "nick": "nick",
            "resource": "resource",
            "class": "get_class",
        }
    )


@pytest.fixture
def device_info(
    api_device_info: ApiDeviceInfo,
    static_device_info: StaticDeviceInfo,
) -> DeviceInfo:
    return DeviceInfo(
        api_device_info,
        static_device_info,
    )


@pytest.fixture
def execute_mock() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def event_bus(execute_mock: AsyncMock, device_info: DeviceInfo) -> EventBus:
    return EventBus(execute_mock, device_info.static.capabilities.get_refresh_commands)


@pytest.fixture
def event_bus_mock(event_bus: EventBus) -> Mock:
    return Mock(spec_set=EventBus, wraps=event_bus)


@pytest.fixture(name="caplog")
def caplog_fixture(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    """Set log level to debug for tests using the caplog fixture."""
    caplog.set_level(logging.DEBUG)
    return caplog
