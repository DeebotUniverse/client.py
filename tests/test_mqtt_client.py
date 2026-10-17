from __future__ import annotations

import asyncio
from contextlib import suppress
import datetime as dt
import logging
import ssl
from typing import TYPE_CHECKING, Any
from unittest.mock import DEFAULT, AsyncMock, MagicMock, Mock, patch

from aiohttp import ClientConnectionError
from aiomqtt import Client, Message, MqttError as AioMqttError
from aiomqtt.exceptions import MqttConnectError
from cachetools import TTLCache
import orjson
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.reasoncodes import ReasonCode
import pytest

from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.volume import SetVolume
from deebot_client.const import UNDEFINED, DataType, UndefinedType
from deebot_client.exceptions import ApiError, AuthenticationError, MqttError
from deebot_client.mqtt_client import MqttClient, MqttConfiguration, create_mqtt_config

from .mqtt_util import subscribe, verify_subscribe

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.models import ApiDeviceInfo, DeviceInfo


@pytest.mark.docker
async def test_last_message_received_at(
    mqtt_config: MqttConfiguration, authenticator: Authenticator
) -> None:
    mqtt_client = MqttClient(mqtt_config, authenticator)
    assert mqtt_client.last_message_received_at is None
    await asyncio.sleep(4)

    # Mock time for assertion
    expected = dt.datetime(2023, 1, 1, tzinfo=dt.UTC)
    with patch("deebot_client.mqtt_client.datetime", wraps=dt.datetime) as mqdt:
        mqdt.now.return_value = expected

        # Simulate message received
        mqtt_client._handle_message(
            Message("/test", b"", 0, retain=False, mid=1, properties=None)
        )

        assert mqtt_client.last_message_received_at == expected


@pytest.mark.docker
async def test_client_bot_subscription(
    mqtt_client: MqttClient, device_info: DeviceInfo, test_mqtt_client: Client
) -> None:
    (_, callback, unsubscribe) = await subscribe(mqtt_client, device_info)

    await verify_subscribe(
        test_mqtt_client, device_info, callback, expected_called=True
    )

    unsubscribe()
    await asyncio.sleep(0.1)

    await verify_subscribe(
        test_mqtt_client, device_info, callback, expected_called=False
    )


@pytest.mark.docker
async def test_client_reconnect_manual(
    mqtt_client: MqttClient, device_info: DeviceInfo, test_mqtt_client: Client
) -> None:
    (_, callback, _) = await subscribe(mqtt_client, device_info)

    await verify_subscribe(
        test_mqtt_client, device_info, callback, expected_called=True
    )

    await mqtt_client.disconnect()
    await verify_subscribe(
        test_mqtt_client, device_info, callback, expected_called=False
    )

    await mqtt_client.connect()
    await asyncio.sleep(0.1)

    await verify_subscribe(
        test_mqtt_client, device_info, callback, expected_called=True
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
) -> bytes:
    data_bytes = orjson.dumps(data)
    if is_request:
        topic = f"iot/p2p/{command_name}/test/test/test/{device_info['did']}/{device_info['class']}/{device_info['resource']}/q/{request_id}/{data_type}"
    else:
        topic = f"iot/p2p/{command_name}/{device_info['did']}/{device_info['class']}/{device_info['resource']}/test/test/test/p/{request_id}/{data_type}"

    await test_mqtt_client.publish(topic, data_bytes)
    await asyncio.sleep(0.1)
    return data_bytes


@pytest.mark.docker
async def test_p2p_success(
    mqtt_client: MqttClient,
    device_info: DeviceInfo,
    test_mqtt_client: Client,
) -> None:
    """Test p2p workflow on SetVolume."""
    (events, _, _) = await subscribe(mqtt_client, device_info)
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
        payload = await _publish_p2p(
            command_name,
            device_info.api,
            {"body": {"data": {"volume": 1}}},
            request_id,
            test_mqtt_client,
            is_request=True,
        )

        create_from_mqtt.assert_called_with(payload)
        assert len(mqtt_client._received_p2p_commands) == 1
        assert mqtt_client._received_p2p_commands[request_id] == command_object

        payload = await _publish_p2p(
            command_name,
            device_info.api,
            {"body": {"data": {"ret": "ok"}}},
            request_id,
            test_mqtt_client,
            is_request=False,
        )

        command_object.handle_mqtt_p2p.assert_called_with(events, payload)
        assert request_id not in mqtt_client._received_p2p_commands
        assert len(mqtt_client._received_p2p_commands) == 0


@pytest.mark.docker
async def test_p2p_not_supported(
    mqtt_client: MqttClient,
    device_info: DeviceInfo,
    test_mqtt_client: Client,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that unsupported command will be logged."""
    await subscribe(mqtt_client, device_info)
    command_name: str = GetBattery.NAME

    await _publish_p2p(
        command_name, device_info.api, {}, "req", test_mqtt_client, is_request=True
    )

    assert (
        "deebot_client.mqtt_client",
        logging.DEBUG,
        f"Command {command_name} does not support p2p handling (yet)",
    ) in caplog.record_tuples


@pytest.mark.docker
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


@pytest.mark.docker
async def test_p2p_to_late(
    mqtt_client: MqttClient,
    device_info: DeviceInfo,
    test_mqtt_client: Client,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test p2p when response comes in to late."""
    # reduce ttl to 1 seconds
    mqtt_client._received_p2p_commands = TTLCache(maxsize=60 * 60, ttl=1)
    await subscribe(mqtt_client, device_info)
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
        payload = await _publish_p2p(
            command_name,
            device_info.api,
            {"body": {"data": {"volume": 1}}},
            request_id,
            test_mqtt_client,
            is_request=True,
        )

        create_from_mqtt.assert_called_with(payload)
        assert len(mqtt_client._received_p2p_commands) == 1
        assert mqtt_client._received_p2p_commands[request_id] == command_object

    await asyncio.sleep(1.1)

    data = {"body": {"data": {"ret": "ok"}}}
    await _publish_p2p(
        command_name,
        device_info.api,
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


@pytest.mark.docker
async def test_p2p_parse_error(
    mqtt_client: MqttClient,
    device_info: DeviceInfo,
    test_mqtt_client: Client,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test p2p parse error."""
    await subscribe(mqtt_client, device_info)

    command_object = Mock(spec=SetVolume)
    command_name = SetVolume.NAME
    command_type = Mock(spec=SetVolume, return_value=command_object)
    with patch.dict(
        "deebot_client.mqtt_client.COMMANDS_WITH_MQTT_P2P_HANDLING",
        {command_name: command_type},
    ):
        request_id = "req"

    payload = await _publish_p2p(
        command_name,
        device_info.api,
        {"volume": 1},
        request_id,
        test_mqtt_client,
        is_request=True,
    )

    assert (
        "deebot_client.mqtt_client",
        logging.ERROR,
        f"An exception occurred during handling p2p message: topic=iot/p2p/{command_name}/test/test/test/did/get_class/resource/q/{request_id}/j; payload={payload!r}",
    ) in caplog.record_tuples


@pytest.mark.docker
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
    ssl_context: ssl.SSLContext | UndefinedType | None,
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


def _failing_client(exception: Exception) -> MagicMock:
    client = MagicMock()
    client.__aenter__.side_effect = exception
    return client


def _connected_then_lost_client() -> MagicMock:
    messages = MagicMock()
    messages.__anext__.side_effect = AioMqttError("Connection lost")
    client = MagicMock()
    client.__aenter__.return_value = client
    client.messages.__aiter__.side_effect = lambda: messages
    return client


async def _run_mqtt_task(
    authenticator: Authenticator, clients: list[MagicMock], sleeps: int | None = None
) -> AsyncMock:
    """Run the mqtt task until the given number of sleeps and return the sleep mock."""
    if sleeps is None:
        sleeps = len(clients)
    sleep_mock = AsyncMock(side_effect=[None] * (sleeps - 1) + [asyncio.CancelledError])
    with (
        patch("deebot_client.mqtt_client.Client", side_effect=clients),
        patch("deebot_client.mqtt_client.asyncio.sleep", sleep_mock),
    ):
        mqtt_client = MqttClient(
            create_mqtt_config(device_id="123", country="IT"), authenticator
        )
        await mqtt_client.connect()
        assert mqtt_client._mqtt_task
        with suppress(asyncio.CancelledError):
            await mqtt_client._mqtt_task

    return sleep_mock


@pytest.mark.parametrize(
    ("exception", "expected_force"),
    [
        pytest.param(
            MqttConnectError(ReasonCode(PacketTypes.CONNACK, "Not authorized")),
            [False, True, False],
            id="not_authorized",
        ),
        pytest.param(
            MqttConnectError(
                ReasonCode(PacketTypes.CONNACK, "Bad user name or password")
            ),
            [False, True, False],
            id="bad_user_name_or_password",
        ),
        pytest.param(
            MqttConnectError(ReasonCode(PacketTypes.CONNACK, "Server unavailable")),
            [False, False, False],
            id="server_unavailable",
        ),
        pytest.param(
            AioMqttError("Connection lost"),
            [False, False, False],
            id="connection_lost",
        ),
    ],
)
async def test_mqtt_task_reauthenticate_on_rejected_credentials(
    authenticator: Authenticator,
    exception: Exception,
    expected_force: list[bool],
) -> None:
    """Test a credential rejection forces one re-authentication."""
    await _run_mqtt_task(authenticator, [_failing_client(exception)] * 3)

    # First call is the credential check in connect()
    assert [
        c.kwargs.get("force", False)
        for c in authenticator.authenticate.await_args_list[1:]  # type: ignore[attr-defined]
    ] == expected_force


async def test_mqtt_task_reconnect_backoff(authenticator: Authenticator) -> None:
    """Test the reconnect interval doubles up to the cap and resets on connect."""
    failing = _failing_client(AioMqttError("Connection refused"))
    connected = _connected_then_lost_client()
    sleep_mock = await _run_mqtt_task(
        authenticator,
        [failing] * 8 + [connected] + [failing] * 2,
    )

    connected.__aexit__.assert_awaited_once()
    assert connected.__aexit__.await_args.args[0] is AioMqttError

    assert [c.args[0] for c in sleep_mock.await_args_list] == [
        5,
        10,
        20,
        40,
        80,
        160,
        300,
        300,
        5,
        10,
        20,
    ]


@pytest.mark.parametrize(
    "exception",
    [
        pytest.param(TimeoutError(), id="timeout"),
        pytest.param(ClientConnectionError(), id="client_error"),
        pytest.param(ApiError(), id="api_error"),
    ],
)
async def test_mqtt_task_retry_transient_error_on_forced_login(
    authenticator: Authenticator, exception: Exception
) -> None:
    """Test a transient error during the forced login is retried with backoff."""
    credentials = authenticator.authenticate.return_value  # type: ignore[attr-defined]
    authenticator.authenticate.side_effect = [  # type: ignore[attr-defined]
        credentials,
        credentials,
        exception,
        exception,
        credentials,
        credentials,
    ]
    rejected = _failing_client(
        MqttConnectError(ReasonCode(PacketTypes.CONNACK, "Not authorized"))
    )
    sleep_mock = await _run_mqtt_task(
        authenticator,
        [rejected, _connected_then_lost_client(), rejected],
        sleeps=5,
    )

    # First call is the credential check in connect()
    assert [
        c.kwargs.get("force", False)
        for c in authenticator.authenticate.await_args_list[1:]  # type: ignore[attr-defined]
    ] == [False, True, True, True, False]
    assert [c.args[0] for c in sleep_mock.await_args_list] == [5, 10, 20, 5, 10]
