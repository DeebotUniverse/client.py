import asyncio
import datetime
import json
import ssl
from collections.abc import Callable
from typing import Any
from unittest.mock import DEFAULT, MagicMock, Mock, patch

import pytest
from aiohttp import ClientSession
from aiomqtt import Client, Message
from cachetools import TTLCache
from testfixtures import LogCapture

from deebot_client.authentication import Authenticator
from deebot_client.commands.battery import GetBattery
from deebot_client.commands.volume import SetVolume
from deebot_client.events.event_bus import EventBus
from deebot_client.exceptions import AuthenticationError
from deebot_client.models import Configuration, DeviceInfo
from deebot_client.mqtt_client import MqttClient, MqttConfiguration, SubscriberInfo

from .fixtures.mqtt_server import MqttServer

_WAITING_AFTER_RESTART = 30


async def _verify_subscribe(
    test_client: Client, device_info: DeviceInfo, expected_called: bool, mock: Mock
) -> None:
    command = "test"
    data = json.dumps({"test": str(datetime.datetime.now())}).encode("utf-8")
    topic = f"iot/atr/{command}/{device_info.did}/{device_info.get_class}/{device_info.resource}/j"
    await test_client.publish(topic, data)

    await asyncio.sleep(0.1)
    if expected_called:
        mock.assert_called_with(command, data)
    else:
        mock.assert_not_called()

    mock.reset_mock()


async def _subscribe(
    mqtt_client: MqttClient, device_info: DeviceInfo
) -> tuple[Mock, Mock, Callable[[], None]]:
    events = Mock(spec=EventBus)
    callback = MagicMock()
    unsubscribe = await mqtt_client.subscribe(
        SubscriberInfo(device_info, events, callback)
    )
    await asyncio.sleep(0.1)
    return (events, callback, unsubscribe)


async def test_last_message_received_at(
    config: Configuration, authenticator: Authenticator
) -> None:
    mqtt_client = MqttClient(MqttConfiguration(config), authenticator)
    assert mqtt_client.last_message_received_at is None
    await asyncio.sleep(4)

    # Mock time for assertion
    expected = datetime.datetime(2023, 1, 1)
    with patch("deebot_client.mqtt_client.datetime", wraps=datetime.datetime) as dt:
        dt.now.return_value = expected

        # Simulate message received
        mqtt_client._handle_message(Message("/test", b"", 0, False, 1, None))

        assert mqtt_client.last_message_received_at == expected


@pytest.mark.timeout(_WAITING_AFTER_RESTART + 10)
async def test_client_reconnect_on_broker_error(
    mqtt_client: MqttClient,
    mqtt_server: MqttServer,
    device_info: DeviceInfo,
    mqtt_config: MqttConfiguration,
) -> None:
    (_, callback, _) = await _subscribe(mqtt_client, device_info)
    async with Client(
        hostname=mqtt_config.hostname,
        port=mqtt_config.port,
        client_id="Test-helper",
        tls_context=mqtt_config.ssl_context,
    ) as client:
        # test client cannot be used as we restart the broker in this test
        await _verify_subscribe(client, device_info, True, callback)

    with LogCapture() as log:
        mqtt_server.stop()
        await asyncio.sleep(0.1)

        log.check_present(
            (
                "deebot_client.mqtt_client",
                "WARNING",
                "Connection lost; Reconnecting in 5 seconds ...",
            )
        )
        log.clear()

        mqtt_server.run()

        for i in range(_WAITING_AFTER_RESTART):
            print(f"Wait for success reconnect... {i}/{_WAITING_AFTER_RESTART}")
            try:
                log.check_present(
                    (
                        "deebot_client.mqtt_client",
                        "DEBUG",
                        "All mqtt tasks created",
                    )
                )
            except AssertionError:
                pass  # Client was not yet connected
            else:
                async with Client(
                    hostname=mqtt_config.hostname,
                    port=mqtt_config.port,
                    client_id="Test-helper",
                    tls_context=mqtt_config.ssl_context,
                ) as client:
                    # test client cannot be used as we restart the broker in this test
                    await _verify_subscribe(client, device_info, True, callback)
                return

            await asyncio.sleep(1)

    pytest.fail("Reconnect failed")


_test_MqttConfiguration_data = [
    ("cn", None, "mq.ecouser.net"),
    ("cn", "localhost", "localhost"),
    ("it", None, "mq-eu.ecouser.net"),
    ("it", "localhost", "localhost"),
]


@pytest.mark.parametrize("set_ssl_context", [True, False])
@pytest.mark.parametrize(
    "country,hostname,expected_hostname", _test_MqttConfiguration_data
)
@pytest.mark.parametrize("device_id", ["test", "123"])
def test_MqttConfiguration(
    set_ssl_context: bool,
    country: str,
    hostname: str | None,
    expected_hostname: str,
    session: ClientSession,
    device_id: str,
) -> None:
    args: dict[str, Any] = {
        "config": Configuration(
            session, device_id=device_id, country=country, continent="eu"
        )
    }
    if set_ssl_context:
        args["ssl_context"] = None

    if hostname is not None:
        args["hostname"] = hostname

    mqtt = MqttConfiguration(**args)
    assert mqtt.hostname == expected_hostname
    assert mqtt.device_id == device_id
    if set_ssl_context:
        assert mqtt.ssl_context is None
    else:
        assert isinstance(mqtt.ssl_context, ssl.SSLContext)


def test_MqttConfiguration_hostname_none(config: Configuration) -> None:
    mqtt = MqttConfiguration(config=config, hostname=None)  # type: ignore[arg-type]
    assert mqtt.hostname == "mq-eu.ecouser.net"


async def test_client_bot_subscription(
    mqtt_client: MqttClient, device_info: DeviceInfo, test_mqtt_client: Client
) -> None:
    (_, callback, unsubscribe) = await _subscribe(mqtt_client, device_info)

    await _verify_subscribe(test_mqtt_client, device_info, True, callback)

    unsubscribe()
    await asyncio.sleep(0.1)

    await _verify_subscribe(test_mqtt_client, device_info, False, callback)


async def test_client_reconnect_manual(
    mqtt_client: MqttClient, device_info: DeviceInfo, test_mqtt_client: Client
) -> None:
    (_, callback, _) = await _subscribe(mqtt_client, device_info)

    await _verify_subscribe(test_mqtt_client, device_info, True, callback)

    await mqtt_client.disconnect()
    await _verify_subscribe(test_mqtt_client, device_info, False, callback)

    await mqtt_client.connect()
    await asyncio.sleep(0.1)

    await _verify_subscribe(test_mqtt_client, device_info, True, callback)


async def _publish_p2p(
    command_name: str,
    device_info: DeviceInfo,
    data: dict[str, Any],
    is_request: bool,
    request_id: str,
    test_mqtt_client: Client,
) -> None:
    data_bytes = json.dumps(data).encode("utf-8")
    if is_request:
        topic = f"iot/p2p/{command_name}/test/test/test/{device_info.did}/{device_info.get_class}/{device_info.resource}/q/{request_id}/j"
    else:
        topic = f"iot/p2p/{command_name}/{device_info.did}/{device_info.get_class}/{device_info.resource}/test/test/test/p/{request_id}/j"

    await test_mqtt_client.publish(topic, data_bytes)
    await asyncio.sleep(0.1)


async def test_p2p_success(
    mqtt_client: MqttClient,
    device_info: DeviceInfo,
    test_mqtt_client: Client,
) -> None:
    """Test p2p workflow on SetVolume."""
    (events, _, _) = await _subscribe(mqtt_client, device_info)
    assert len(mqtt_client._received_p2p_commands) == 0

    command_object = Mock(spec=SetVolume)
    command_name = SetVolume.name
    command_type = Mock(spec=SetVolume, return_value=command_object)
    with patch.dict(
        "deebot_client.mqtt_client.COMMANDS_WITH_MQTT_P2P_HANDLING",
        {command_name: command_type},
    ):
        request_id = "req"
        data: dict[str, Any] = {"body": {"data": {"volume": 1}}}
        await _publish_p2p(
            command_name, device_info, data, True, request_id, test_mqtt_client
        )

        command_type.assert_called_with(**(data["body"]["data"]))
        assert len(mqtt_client._received_p2p_commands) == 1
        assert mqtt_client._received_p2p_commands[request_id] == command_object

        data = {"body": {"data": {"ret": "ok"}}}
        await _publish_p2p(
            command_name, device_info, data, False, request_id, test_mqtt_client
        )

        command_object.handle_mqtt_p2p.assert_called_with(events, data)
        assert request_id not in mqtt_client._received_p2p_commands
        assert len(mqtt_client._received_p2p_commands) == 0


async def test_p2p_not_supported(
    mqtt_client: MqttClient,
    device_info: DeviceInfo,
    test_mqtt_client: Client,
) -> None:
    """Test that unsupported command will be logged."""
    await _subscribe(mqtt_client, device_info)
    command_name: str = GetBattery.name

    with LogCapture() as log:
        await _publish_p2p(command_name, device_info, {}, True, "req", test_mqtt_client)

        log.check_present(
            (
                "deebot_client.mqtt_client",
                "DEBUG",
                f"Command {command_name} does not support p2p handling (yet)",
            )
        )


async def test_p2p_to_late(
    mqtt_client: MqttClient,
    device_info: DeviceInfo,
    test_mqtt_client: Client,
) -> None:
    """Test p2p when response comes in to late."""
    # reduce ttl to 1 seconds
    mqtt_client._received_p2p_commands = TTLCache(maxsize=60 * 60, ttl=1)
    await _subscribe(mqtt_client, device_info)
    assert len(mqtt_client._received_p2p_commands) == 0

    command_object = Mock(spec=SetVolume)
    command_name = SetVolume.name
    command_type = Mock(spec=SetVolume, return_value=command_object)
    with patch.dict(
        "deebot_client.mqtt_client.COMMANDS_WITH_MQTT_P2P_HANDLING",
        {command_name: command_type},
    ):
        request_id = "req"
        data: dict[str, Any] = {"body": {"data": {"volume": 1}}}
        await _publish_p2p(
            command_name, device_info, data, True, request_id, test_mqtt_client
        )

        command_type.assert_called_with(**(data["body"]["data"]))
        assert len(mqtt_client._received_p2p_commands) == 1
        assert mqtt_client._received_p2p_commands[request_id] == command_object

    with LogCapture() as log:
        await asyncio.sleep(1.1)

        data = {"body": {"data": {"ret": "ok"}}}
        await _publish_p2p(
            command_name, device_info, data, False, request_id, test_mqtt_client
        )

        command_object.handle_mqtt_p2p.assert_not_called()
        log.check_present(
            (
                "deebot_client.mqtt_client",
                "DEBUG",
                f"Response to command came in probably to late. requestId={request_id}, commandName={command_name}",
            )
        )


async def test_p2p_parse_error(
    mqtt_client: MqttClient,
    device_info: DeviceInfo,
    test_mqtt_client: Client,
) -> None:
    """Test p2p parse error."""
    await _subscribe(mqtt_client, device_info)

    command_object = Mock(spec=SetVolume)
    command_name = SetVolume.name
    command_type = Mock(spec=SetVolume, return_value=command_object)
    with patch.dict(
        "deebot_client.mqtt_client.COMMANDS_WITH_MQTT_P2P_HANDLING",
        {command_name: command_type},
    ):
        request_id = "req"
        data: dict[str, Any] = {"volume": 1}

    with LogCapture() as log:
        await _publish_p2p(
            command_name, device_info, data, True, request_id, test_mqtt_client
        )

        log.check_present(
            (
                "deebot_client.mqtt_client",
                "WARNING",
                f"Could not parse p2p payload: topic=iot/p2p/{command_name}/test/test/test/did/get_class/resource/q/{request_id}/j; payload={data}",
            )
        )


@pytest.mark.parametrize(
    "exception_to_raise, expected_log_message",
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
) -> None:
    with patch(
        "deebot_client.mqtt_client.Client",
        MagicMock(side_effect=[exception_to_raise, DEFAULT]),
    ):
        with LogCapture() as log:
            mqtt_client = MqttClient(mqtt_config, authenticator)

            await mqtt_client.connect()
            await asyncio.sleep(0.1)

            log.check_present(
                (
                    "deebot_client.mqtt_client",
                    "ERROR",
                    expected_log_message,
                )
            )

            assert mqtt_client._mqtt_task
            assert mqtt_client._mqtt_task.done()

            await mqtt_client.connect()
            await asyncio.sleep(0.1)

            assert not mqtt_client._mqtt_task.done()
