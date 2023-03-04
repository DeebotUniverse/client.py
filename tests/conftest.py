import logging
from collections.abc import AsyncGenerator

import aiohttp
import pytest

from deebot_client._api_client import _InternalApiClient
from deebot_client.api_client import ApiClient
from deebot_client.authentication import Authenticator
from deebot_client.models import Configuration
from deebot_client.util import md5


@pytest.fixture
async def config() -> AsyncGenerator:
    async with aiohttp.ClientSession() as session:
        logging.basicConfig(level=logging.DEBUG)
        configuration = Configuration(
            session,
            device_id="Test_device",
            country="it",
            continent="eu",
        )

        yield configuration


@pytest.fixture
def internal_api_client(config: Configuration) -> _InternalApiClient:
    return _InternalApiClient(config)


@pytest.fixture
def authenticator(
    config: Configuration, internal_api_client: _InternalApiClient
) -> Authenticator:
    return Authenticator(config, internal_api_client, "test@test.com", md5("test"))


@pytest.fixture
def api_client(
    internal_api_client: _InternalApiClient, authenticator: Authenticator
) -> ApiClient:
    return ApiClient(internal_api_client, authenticator)
