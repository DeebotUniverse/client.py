"""Unit tests for MQTT client without requiring Docker."""

from __future__ import annotations

import ssl
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from aiohttp import ClientSession
from aiomqtt import MqttError as AioMqttError
import pytest

from deebot_client.authentication import Authenticator, create_rest_config
from deebot_client.exceptions import MqttError
from deebot_client.models import Credentials
from deebot_client.mqtt_client import MqttClient, create_mqtt_config

if TYPE_CHECKING:
    from deebot_client.authentication import RestConfiguration
    from deebot_client.mqtt_client import MqttConfiguration


@pytest.mark.parametrize(
    ("override_url", "expected_hostname", "expected_port", "expected_ssl"),
    [
        ("mqtt://example.com:1234", "example.com", 1234, None),
        ("mqtt://example.com", "example.com", 1883, None),
        ("mqtts://secure.example.com", "secure.example.com", 8883, True),
        ("mqtts://secure.example.com:9999", "secure.example.com", 9999, True),
    ],
)
def test_create_mqtt_config_with_override(
    override_url: str,
    expected_hostname: str,
    expected_port: int,
    expected_ssl: bool | None,
) -> None:
    """Test MQTT configuration with override URL."""
    config = create_mqtt_config(
        device_id="test_device",
        country="IT",
        override_mqtt_url=override_url,
    )

    assert config.hostname == expected_hostname
    assert config.port == expected_port
    assert config.device_id == "test_device"
    if expected_ssl is True:
        assert config.ssl_context is not None
        assert isinstance(config.ssl_context, ssl.SSLContext)
    elif expected_ssl is None:
        assert config.ssl_context is None


def test_create_mqtt_config_invalid_scheme() -> None:
    """Test MQTT configuration with invalid scheme."""
    with pytest.raises(MqttError, match="Invalid scheme"):
        create_mqtt_config(
            device_id="test_device",
            country="IT",
            override_mqtt_url="http://example.com",
        )


def test_create_mqtt_config_missing_hostname() -> None:
    """Test MQTT configuration with missing hostname."""
    with pytest.raises(MqttError, match="Hostname is required"):
        create_mqtt_config(
            device_id="test_device",
            country="IT",
            override_mqtt_url="mqtt://",
        )


def test_create_mqtt_config_default() -> None:
    """Test MQTT configuration with default settings."""
    config = create_mqtt_config(
        device_id="test_device",
        country="IT",
    )

    assert config.hostname == "mq-eu.ecouser.net"
    assert config.port == 443
    assert config.ssl_context is not None
    assert config.ssl_context.check_hostname is False
    assert config.ssl_context.verify_mode == ssl.CERT_NONE


def test_create_mqtt_config_custom_ssl_context() -> None:
    """Test MQTT configuration with custom SSL context."""
    custom_ssl = ssl.create_default_context()
    config = create_mqtt_config(
        device_id="test_device",
        country="IT",
        ssl_context=custom_ssl,
    )

    assert config.ssl_context == custom_ssl


def test_create_mqtt_config_disable_ssl() -> None:
    """Test MQTT configuration with SSL disabled."""
    config = create_mqtt_config(
        device_id="test_device",
        country="IT",
        override_mqtt_url="mqtt://example.com",
        ssl_context=None,
    )

    assert config.ssl_context is None


@pytest.fixture
def simple_mqtt_config() -> MqttConfiguration:
    """Provide a simple MQTT config without docker."""
    return create_mqtt_config(
        device_id="test_device",
        country="IT",
        override_mqtt_url="mqtt://localhost:1883",
    )


@pytest.fixture
async def simple_authenticator(session: ClientSession) -> Authenticator:
    """Provide a simple authenticator without docker."""
    rest_config = create_rest_config(
        session=session,
        device_id="test_device",
        alpha_2_country="IT",
    )

    authenticator = Mock(spec_set=Authenticator)
    authenticator.authenticate.return_value = Credentials("token", "user_id", 9999)
    authenticator.subscribe = Mock()

    return authenticator


async def test_verify_config_success(
    simple_mqtt_config: MqttConfiguration,
    simple_authenticator: Authenticator,
) -> None:
    """Test verify_config with successful connection."""
    mqtt_client = MqttClient(simple_mqtt_config, simple_authenticator)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(mqtt_client, "_get_client", return_value=mock_client):
        await mqtt_client.verify_config()  # Should not raise


async def test_verify_config_failure(
    simple_mqtt_config: MqttConfiguration,
    simple_authenticator: Authenticator,
) -> None:
    """Test verify_config with connection failure."""
    mqtt_client = MqttClient(simple_mqtt_config, simple_authenticator)

    with patch.object(mqtt_client, "_get_client", side_effect=AioMqttError("Connection failed")):
        with pytest.raises(MqttError, match="Cannot connect"):
            await mqtt_client.verify_config()


async def test_last_message_received_at_property(
    simple_mqtt_config: MqttConfiguration,
    simple_authenticator: Authenticator,
) -> None:
    """Test last_message_received_at property."""
    mqtt_client = MqttClient(simple_mqtt_config, simple_authenticator)
    assert mqtt_client.last_message_received_at is None


async def test_get_client(
    simple_mqtt_config: MqttConfiguration,
    simple_authenticator: Authenticator,
) -> None:
    """Test _get_client method."""
    mqtt_client = MqttClient(simple_mqtt_config, simple_authenticator)

    client = await mqtt_client._get_client()

    assert client is not None
    # Just verify the client was created, can't easily check client_id
    # as it's internal to aiomqtt.Client


async def test_connect_creates_task(
    simple_mqtt_config: MqttConfiguration,
    simple_authenticator: Authenticator,
) -> None:
    """Test that connect creates MQTT task."""
    mqtt_client = MqttClient(simple_mqtt_config, simple_authenticator)

    assert mqtt_client._mqtt_task is None

    with patch.object(mqtt_client, "_create_mqtt_task", new_callable=AsyncMock) as mock_create:
        await mqtt_client.connect()
        mock_create.assert_awaited_once()


async def test_connect_does_not_recreate_running_task(
    simple_mqtt_config: MqttConfiguration,
    simple_authenticator: Authenticator,
) -> None:
    """Test that connect does not recreate a running task."""
    mqtt_client = MqttClient(simple_mqtt_config, simple_authenticator)

    # Create a mock task that is not done
    mock_task = MagicMock()
    mock_task.done.return_value = False
    mqtt_client._mqtt_task = mock_task

    with patch.object(mqtt_client, "_create_mqtt_task", new_callable=AsyncMock) as mock_create:
        await mqtt_client.connect()
        mock_create.assert_not_awaited()


async def test_disconnect_cancels_task(
    simple_mqtt_config: MqttConfiguration,
    simple_authenticator: Authenticator,
) -> None:
    """Test that disconnect cancels MQTT task."""
    mqtt_client = MqttClient(simple_mqtt_config, simple_authenticator)

    with patch.object(mqtt_client, "_cancel_mqtt_task", new_callable=AsyncMock) as mock_cancel:
        await mqtt_client.disconnect()
        mock_cancel.assert_awaited_once()


async def test_cancel_mqtt_task_with_active_task(
    simple_mqtt_config: MqttConfiguration,
    simple_authenticator: Authenticator,
) -> None:
    """Test _cancel_mqtt_task with active task."""
    mqtt_client = MqttClient(simple_mqtt_config, simple_authenticator)

    # Create a proper asyncio task for testing cancellation
    async def dummy_task() -> None:
        await asyncio.sleep(10)

    import asyncio
    mqtt_client._mqtt_task = asyncio.create_task(dummy_task())

    await mqtt_client._cancel_mqtt_task()

    # Task should be cancelled
    assert mqtt_client._mqtt_task.cancelled()


async def test_cancel_mqtt_task_with_no_task(
    simple_mqtt_config: MqttConfiguration,
    simple_authenticator: Authenticator,
) -> None:
    """Test _cancel_mqtt_task with no task."""
    mqtt_client = MqttClient(simple_mqtt_config, simple_authenticator)

    mqtt_client._mqtt_task = None
    await mqtt_client._cancel_mqtt_task()  # Should not raise


async def test_cancel_mqtt_task_already_done(
    simple_mqtt_config: MqttConfiguration,
    simple_authenticator: Authenticator,
) -> None:
    """Test _cancel_mqtt_task when task is already done."""
    mqtt_client = MqttClient(simple_mqtt_config, simple_authenticator)

    # Create a task that completes immediately
    async def dummy_task() -> None:
        pass

    import asyncio
    mqtt_client._mqtt_task = asyncio.create_task(dummy_task())
    await asyncio.sleep(0.01)  # Let task complete

    # Task is done, cancel should return False
    await mqtt_client._cancel_mqtt_task()  # Should not raise
