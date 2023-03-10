import logging
from collections.abc import AsyncGenerator

import aiohttp
import pytest

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
def authenticator(config: Configuration) -> Authenticator:
    return Authenticator(config, "test@test.com", md5("test"))


@pytest.fixture
def api_client(authenticator: Authenticator) -> ApiClient:
    return ApiClient(authenticator)
