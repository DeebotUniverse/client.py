import logging
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest
from aiomqtt import Client

from deebot_client.api_client import ApiClient
from deebot_client.authentication import Authenticator
from deebot_client.events.event_bus import EventBus
from deebot_client.models import Configuration, Credentials, DeviceInfo
from deebot_client.mqtt_client import MqttClient, MqttConfiguration
from deebot_client.vacuum_bot import VacuumBot

from .fixtures.mqtt_server import MqttServer


@pytest.fixture
async def session() -> AsyncGenerator:
    async with aiohttp.ClientSession() as client_session:
        logging.basicConfig(level=logging.DEBUG)
        yield client_session


@pytest.fixture
async def config(session: aiohttp.ClientSession) -> AsyncGenerator:
    configuration = Configuration(
        session,
        device_id="Test_device",
        country="it",
        continent="eu",
    )

    yield configuration


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
    return MqttConfiguration(
        config=config,
        hostname="localhost",
        port=mqtt_server.get_port(),
        ssl_context=None,
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
        client_id="Test-helper",
        tls_context=mqtt_config.ssl_context,
    ) as client:
        yield client


@pytest.fixture
def device_info() -> DeviceInfo:
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
        }
    )


@pytest.fixture
async def vacuum_bot(
    device_info: DeviceInfo, authenticator: Authenticator
) -> AsyncGenerator[VacuumBot, None]:
    mqtt = Mock(spec_set=MqttClient)
    bot = VacuumBot(device_info, authenticator)
    await bot.initialize(mqtt)
    yield bot
    await bot.teardown()


@pytest.fixture
def execute_mock() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def event_bus(execute_mock: AsyncMock) -> EventBus:
    return EventBus(execute_mock)
