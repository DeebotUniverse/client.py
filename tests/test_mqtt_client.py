from __future__ import annotations

import asyncio
import datetime
import json
import logging
import ssl
from typing import TYPE_CHECKING, Any
from unittest.mock import DEFAULT, MagicMock, Mock, patch

from aiomqtt import Client, Message, MqttError as AioMqttError
from cachetools import TTLCache
import pytest

from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.volume import SetVolume
from deebot_client.const import UNDEFINED, DataType, UndefinedType
from deebot_client.exceptions import AuthenticationError, MqttError
from deebot_client.mqtt_client import MqttClient, MqttConfiguration, create_mqtt_config

from .mqtt_util import subscribe, verify_subscribe

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.models import ApiDeviceInfo


async def test_last_message_received_at(
    mqtt_config: MqttConfiguration, authenticator: Authenticator
) -> None:
    mqtt_client = MqttClient(mqtt_config, authenticator)
    assert mqtt_client.last_message_received_at is None
    await asyncio.sleep(4)

    # Mock time for assertion
    expected = datetime.datetime(2023, 1, 1)
    with patch("deebot_client.mqtt_client.datetime", wraps=datetime.datetime) as dt:
        dt.now.return_value = expected

        # Simulate message received
        mqtt_client._handle_message(
            Message("/test", b"", 0, retain=False, mid=1, properties=None)
        )

        assert mqtt_client.last_message_received_at == expected


async def test_client_bot_subscription(
    mqtt_client: MqttClient, api_device_info: ApiDeviceInfo, test_mqtt_client: Client
) -> None:
    (_, callback, unsubscribe) = await subscribe(mqtt_client, api_device_info)

    await verify_subscribe(
        test_mqtt_client, api_device_info, callback, expected_called=True
    )

    unsubscribe()
    await asyncio.sleep(0.1)

    await verify_subscribe(
        test_mqtt_client, api_device_info, callback, expected_called=False
    )


async def test_client_reconnect_manual(
    mqtt_client: MqttClient, api_device_info: ApiDeviceInfo, test_mqtt_client: Client
) -> None:
    (_, callback, _) = await subscribe(mqtt_client, api_device_info)

    await verify_subscribe(
        test_mqtt_client, api_device_info, callback, expected_called=True
    )

    await mqtt_client.disconnect()
    await verify_subscribe(
        test_mqtt_client, api_device_info, callback, expected_called=False
    )

    await mqtt_client.connect()
    await asyncio.sleep(0.1)

    await verify_subscribe(
        test_mqtt_client, api_device_info, callback, expected_called=True
    )


async def _publish_p2p(
    command_name: str,
    device_info: ApiDeviceInfo,
    data: dict[str, Any],
    request_id: str,
    test_mqtt_client: Client,
    data_type: str = "j",
    *,
    is_request: bool,
) -> None:
    data_bytes = json.dumps(data).encode("utf-8")
    if is_request:
        topic = f"iot/p2p/{command_name}/test/test/test/{device_info['did']}/{device_info['class']}/{device_info['resource']}/q/{request_id}/{data_type}"
    else:
        topic = f"iot/p2p/{command_name}/{device_info['did']}/{device_info['class']}/{device_info['resource']}/test/test/test/p/{request_id}/{data_type}"

    await test_mqtt_client.publish(topic, data_bytes)
    await asyncio.sleep(0.1)


async def test_p2p_success(
    mqtt_client: MqttClient,
    api_device_info: ApiDeviceInfo,
    test_mqtt_client: Client,
) -> None:
    """Test p2p workflow on SetVolume."""
    (events, _, _) = await subscribe(mqtt_client, api_device_info)
    assert len(mqtt_client._received_p2p_commands) == 0

    command_object = Mock(spec=SetVolume)
    command_name = SetVolume.NAME
    command_type = Mock(spec=SetVolume)
    create_from_mqtt = command_type.create_from_mqtt
    create_from_mqtt.return_value = command_object
    with patch.dict(
        "deebot_client.mqtt_client.COMMANDS_WITH_MQTT_P2P_HANDLING",
        {DataType.JSON: {command_name: command_type}},
    ):
        request_id = "req"
        data: dict[str, Any] = {"body": {"data": {"volume": 1}}}
        await _publish_p2p(
            command_name,
            api_device_info,
            data,
            request_id,
            test_mqtt_client,
            is_request=True,
        )

        create_from_mqtt.assert_called_with(data["body"]["data"])
        assert len(mqtt_client._received_p2p_commands) == 1
        assert mqtt_client._received_p2p_commands[request_id] == command_object

        data = {"body": {"data": {"ret": "ok"}}}
        await _publish_p2p(
            command_name,
            api_device_info,
            data,
            request_id,
            test_mqtt_client,
            is_request=False,
        )

        command_object.handle_mqtt_p2p.assert_called_with(events, data)
        assert request_id not in mqtt_client._received_p2p_commands
        assert len(mqtt_client._received_p2p_commands) == 0


async def test_p2p_not_supported(
    mqtt_client: MqttClient,
    api_device_info: ApiDeviceInfo,
    test_mqtt_client: Client,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that unsupported command will be logged."""
    await subscribe(mqtt_client, api_device_info)
    command_name: str = GetBattery.NAME

    await _publish_p2p(
        command_name, api_device_info, {}, "req", test_mqtt_client, is_request=True
    )

    assert (
        "deebot_client.mqtt_client",
        logging.DEBUG,
        f"Command {command_name} does not support p2p handling (yet)",
    ) in caplog.record_tuples


async def test_p2p_data_type_not_supported(
    mqtt_client: MqttClient, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that unsupported command will be logged."""
    topic_split = [
        "iot",
        "p2p",
        "getBattery",
        "test",
        "test",
        "test",
        "did",
        "get_class",
        "resource",
        "q",
        "req",
        "z",
    ]

    mqtt_client._handle_p2p(topic_split, "")

    assert (
        "deebot_client.mqtt_client",
        logging.WARNING,
        'Unsupported data type: "z"',
    ) in caplog.record_tuples


async def test_p2p_to_late(
    mqtt_client: MqttClient,
    api_device_info: ApiDeviceInfo,
    test_mqtt_client: Client,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test p2p when response comes in to late."""
    # reduce ttl to 1 seconds
    mqtt_client._received_p2p_commands = TTLCache(maxsize=60 * 60, ttl=1)
    await subscribe(mqtt_client, api_device_info)
    assert len(mqtt_client._received_p2p_commands) == 0

    command_object = Mock(spec=SetVolume)
    command_name = SetVolume.NAME
    command_type = Mock(spec=SetVolume)
    create_from_mqtt = command_type.create_from_mqtt
    create_from_mqtt.return_value = command_object
    with patch.dict(
        "deebot_client.mqtt_client.COMMANDS_WITH_MQTT_P2P_HANDLING",
        {DataType.JSON: {command_name: command_type}},
    ):
        request_id = "req"
        data: dict[str, Any] = {"body": {"data": {"volume": 1}}}
        await _publish_p2p(
            command_name,
            api_device_info,
            data,
            request_id,
            test_mqtt_client,
            is_request=True,
        )

        create_from_mqtt.assert_called_with(data["body"]["data"])
        assert len(mqtt_client._received_p2p_commands) == 1
        assert mqtt_client._received_p2p_commands[request_id] == command_object

    await asyncio.sleep(1.1)

    data = {"body": {"data": {"ret": "ok"}}}
    await _publish_p2p(
        command_name,
        api_device_info,
        data,
        request_id,
        test_mqtt_client,
        is_request=False,
    )

    command_object.handle_mqtt_p2p.assert_not_called()
    assert (
        "deebot_client.mqtt_client",
        logging.DEBUG,
        f"Response to command came in probably to late. requestId={request_id}, commandName={command_name}",
    ) in caplog.record_tuples


async def test_p2p_parse_error(
    mqtt_client: MqttClient,
    api_device_info: ApiDeviceInfo,
    test_mqtt_client: Client,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test p2p parse error."""
    await subscribe(mqtt_client, api_device_info)

    command_object = Mock(spec=SetVolume)
    command_name = SetVolume.NAME
    command_type = Mock(spec=SetVolume, return_value=command_object)
    with patch.dict(
        "deebot_client.mqtt_client.COMMANDS_WITH_MQTT_P2P_HANDLING",
        {command_name: command_type},
    ):
        request_id = "req"
        data: dict[str, Any] = {"volume": 1}

    await _publish_p2p(
        command_name,
        api_device_info,
        data,
        request_id,
        test_mqtt_client,
        is_request=True,
    )

    assert (
        "deebot_client.mqtt_client",
        logging.WARNING,
        f"Could not parse p2p payload: topic=iot/p2p/{command_name}/test/test/test/did/get_class/resource/q/{request_id}/j; payload={data}",
    ) in caplog.record_tuples


@pytest.mark.parametrize(
    ("exception_to_raise", "expected_log_message"),
    [
        (
            AuthenticationError,
            "Could not authenticate. Please check your credentials and afterwards reload the integration.",
        ),
        (RuntimeError, "An exception occurred"),
    ],
)
async def test_mqtt_task_exceptions(
    authenticator: Authenticator,
    mqtt_config: MqttConfiguration,
    exception_to_raise: Exception,
    expected_log_message: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with patch(
        "deebot_client.mqtt_client.Client",
        MagicMock(side_effect=[exception_to_raise, DEFAULT]),
    ):
        mqtt_client = MqttClient(mqtt_config, authenticator)

        await mqtt_client.connect()
        await asyncio.sleep(0.1)

        assert (
            "deebot_client.mqtt_client",
            logging.ERROR,
            expected_log_message,
        ) in caplog.record_tuples

        assert mqtt_client._mqtt_task
        assert mqtt_client._mqtt_task.done()

        await mqtt_client.connect()
        await asyncio.sleep(0.1)

        assert not mqtt_client._mqtt_task.done()


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
@pytest.mark.parametrize("ssl_context", [UNDEFINED, None, ssl.create_default_context()])
def test_config(
    authenticator: Authenticator,
    country: str,
    device_id: str,
    override_mqtt_url: str | None,
    expected_hostname: str,
    expected_port: int,
    ssl_context: ssl.SSLContext | None | UndefinedType,
    *,
    expect_ssl_context: bool,
) -> None:
    """Test mqtt part of the configuration."""
    client = MqttClient(
        create_mqtt_config(
            device_id=device_id,
            country=country,
            override_mqtt_url=override_mqtt_url,
            ssl_context=ssl_context,
        ),
        authenticator,
    )
    config = client._config
    assert config.hostname == expected_hostname
    assert config.device_id == device_id
    assert config.port == expected_port
    if isinstance(ssl_context, ssl.SSLContext) or (
        expect_ssl_context and isinstance(ssl_context, UndefinedType)
    ):
        assert isinstance(config.ssl_context, ssl.SSLContext)
    else:
        assert config.ssl_context is None


@pytest.mark.parametrize(
    ("override_mqtt_url", "error_msg"),
    [
        ("http://test", "Invalid scheme. Expecting mqtt or mqtts"),
        ("mqtt://:80", "Hostname is required"),
        ("mqtt://", "Hostname is required"),
    ],
)
def test_config_override_mqtt_url_invalid(
    authenticator: Authenticator, override_mqtt_url: str, error_msg: str
) -> None:
    """Test that an invalid mqtt override url will raise a DeebotError."""
    with pytest.raises(MqttError, match=error_msg):
        MqttClient(
            create_mqtt_config(
                device_id="123",
                country="IT",
                override_mqtt_url=override_mqtt_url,
            ),
            authenticator,
        )


async def test_verify_config(authenticator: Authenticator) -> None:
    with patch("deebot_client.mqtt_client.Client", autospec=True) as client_mock:
        client = MqttClient(
            create_mqtt_config(
                device_id="123",
                country="IT",
            ),
            authenticator,
        )

        await client.verify_config()
        client_mock.return_value.__aenter__.assert_called()


async def test_verify_config_fails(authenticator: Authenticator) -> None:
    with patch("deebot_client.mqtt_client.Client", autospec=True) as client_mock:
        client_mock.return_value.__aenter__.side_effect = AioMqttError
        client = MqttClient(
            create_mqtt_config(
                device_id="123",
                country="IT",
            ),
            authenticator,
        )

        with pytest.raises(MqttError, match="Cannot connect"):
            await client.verify_config()

        client_mock.return_value.__aenter__.assert_called()
