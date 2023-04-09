import asyncio
import datetime
import ssl
from typing import Any
from unittest.mock import Mock, patch

import pytest
from aiohttp import ClientSession
from gmqtt import Client

from deebot_client.models import Configuration, DeviceInfo
from deebot_client.mqtt_client import MqttClient, MqttConfiguration
from deebot_client.vacuum_bot import VacuumBot

from .fixtures.mqtt_server import MqttServer


async def _verify_subscribe(
    test_client: Client, bot: Mock, expected_called: bool
) -> None:
    device_info = bot.device_info
    command = "test"
    data = {"test": str(datetime.datetime.now())}
    topic = f"iot/atr/{command}/{device_info.did}/{device_info.get_class}/{device_info.resource}/j"
    test_client.publish(topic, data)

    await asyncio.sleep(0.1)
    if expected_called:
        bot.handle_message.assert_called_with(command, data)
    else:
        bot.handle_message.assert_not_called()

    bot.handle_message.reset_mock()


async def test_last_message_received_at(mqtt_client: MqttClient) -> None:
    assert mqtt_client.last_message_received_at is None
    await asyncio.sleep(4)

    # Mock time for assertion
    expected = datetime.datetime(2023, 1, 1)
    with patch("deebot_client.mqtt_client.datetime", wraps=datetime.datetime) as dt:
        dt.now.return_value = expected

        # Simulate message received
        await mqtt_client._on_message(None, "/test", b"", 0, {})

        assert mqtt_client.last_message_received_at == expected


_WAITING_AFTER_RESTART = 30


@pytest.mark.timeout(_WAITING_AFTER_RESTART + 10)
async def test_client_reconnect_on_broker_error(
    mqtt_client: MqttClient,
    mqtt_server: MqttServer,
    device_info: DeviceInfo,
    test_mqtt_client: Client,
) -> None:
    assert mqtt_client._client is not None
    bot = Mock(spec=VacuumBot)
    bot.device_info = device_info
    await mqtt_client.subscribe(bot)

    await _verify_subscribe(test_mqtt_client, bot, True)

    mqtt_server.stop()
    await asyncio.sleep(0.1)
    assert not mqtt_client._client.is_connected

    mqtt_server.run()

    for i in range(_WAITING_AFTER_RESTART):
        print(f"Wait for success reconnect... {i}/{_WAITING_AFTER_RESTART}")
        if mqtt_client._client.is_connected:
            await _verify_subscribe(test_mqtt_client, bot, True)
            return

        await asyncio.sleep(1)

    pytest.fail("Reconnect failed")


_test_MqttConfiguration_data = [
    ("cn", None, "mq.ecouser.net"),
    ("cn", "localhost", "localhost"),
    ("it", None, "mq-eu.ecouser.net"),
    ("it", "localhost", "localhost"),
]


@pytest.mark.parametrize("ssl_context", [None, False])
@pytest.mark.parametrize(
    "country,hostname,expected_hostname", _test_MqttConfiguration_data
)
@pytest.mark.parametrize("device_id", ["test", "123"])
def test_MqttConfiguration(
    ssl_context: None | bool,
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
    if ssl_context is not None:
        args["ssl_context"] = ssl_context

    if hostname is not None:
        args["hostname"] = hostname

    mqtt = MqttConfiguration(**args)
    assert mqtt.hostname == expected_hostname
    assert mqtt.device_id == device_id
    if ssl_context is None:
        assert isinstance(mqtt.ssl_context, ssl.SSLContext)
    else:
        assert mqtt.ssl_context == ssl_context


def test_MqttConfiguration_hostname_none(config: Configuration) -> None:
    mqtt = MqttConfiguration(config=config, hostname=None)  # type: ignore[arg-type]
    assert mqtt.hostname == "mq-eu.ecouser.net"


async def test_client_bot_subscription(
    mqtt_client: MqttClient, device_info: DeviceInfo, test_mqtt_client: Client
) -> None:
    bot = Mock(spec=VacuumBot)
    bot.device_info = device_info
    await mqtt_client.subscribe(bot)

    await _verify_subscribe(test_mqtt_client, bot, True)

    mqtt_client.unsubscribe(bot)

    await _verify_subscribe(test_mqtt_client, bot, False)


async def test_client_reconnect_manual(
    mqtt_client: MqttClient, device_info: DeviceInfo, test_mqtt_client: Client
) -> None:
    bot = Mock(spec=VacuumBot)
    bot.device_info = device_info
    await mqtt_client.subscribe(bot)

    await _verify_subscribe(test_mqtt_client, bot, True)

    await mqtt_client.disconnect()
    await _verify_subscribe(test_mqtt_client, bot, False)

    await mqtt_client.connect()
    await _verify_subscribe(test_mqtt_client, bot, True)
