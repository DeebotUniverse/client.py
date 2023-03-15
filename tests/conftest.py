import logging
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest

from deebot_client.api_client import ApiClient
from deebot_client.authentication import Authenticator
from deebot_client.models import Configuration, Credentials, DeviceInfo
from deebot_client.mqtt_client import MqttClient, MqttConnectionConfig

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
def authenticator(config: Configuration) -> Authenticator:
    authenticator = Mock(spec_set=Authenticator)
    authenticator.authenticate = AsyncMock(
        return_value=Credentials("token", "user_id", 9999)
    )
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
def mqtt_config(config: Configuration, mqtt_server: MqttServer) -> MqttConnectionConfig:
    return MqttConnectionConfig(
        config=config,
        hostname="localhost",
        port=int(mqtt_server.get_port()),
        ssl_context=False,
    )


@pytest.fixture
def mqtt_client(
    config: Configuration,
    authenticator: Authenticator,
    mqtt_config: MqttConnectionConfig,
) -> MqttClient:
    return MqttClient(config, authenticator, mqtt_config)


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
