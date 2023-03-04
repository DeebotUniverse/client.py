import datetime
from unittest.mock import patch

from deebot_client.authentication import Authenticator
from deebot_client.models import Configuration
from deebot_client.mqtt_client import MqttClient


async def test_last_message_received_at(
    config: Configuration, authenticator: Authenticator
) -> None:
    client = MqttClient(config, authenticator)
    assert client.last_message_received_at is None

    # Mock time for assertion
    expected = datetime.datetime(2023, 1, 1)
    with patch("deebot_client.mqtt_client.datetime", wraps=datetime.datetime) as dt:
        dt.now.return_value = expected

        # Simulate message received
        await client._on_message(None, "/test", b"", 0, {})

        assert client.last_message_received_at == expected
