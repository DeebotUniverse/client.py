import asyncio
import datetime
from unittest.mock import Mock, patch

import pytest
from aiohttp import ClientSession

from deebot_client.models import Configuration, DeviceInfo
from deebot_client.mqtt_client import MqttClient, MqttConnectionConfig
from deebot_client.vacuum_bot import VacuumBot

from .fixtures.mqtt_server import MqttServer


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


_WAINTING_AFTER_RESTART = 30


@pytest.mark.timeout(_WAINTING_AFTER_RESTART + 10)
async def test_client_reconnect(
    mqtt_client: MqttClient, mqtt_server: MqttServer, device_info: DeviceInfo
) -> None:
    await mqtt_client.initialize()
    assert mqtt_client._client is not None
    assert mqtt_client._client.is_connected

    bot = Mock(spec=VacuumBot)
    bot.device_info = device_info
    mqtt_client.subscribe(bot)

    async def verify_subscribe(num: int) -> None:
        command = "test"
        data = {"test": num}
        topic = f"iot/atr/{command}/{device_info.did}/{device_info.get_class}/{device_info.resource}/j"
        assert mqtt_client._client is not None
        mqtt_client._client.publish(topic, data)

        await asyncio.sleep(0.1)
        bot.handle_message.assert_called_with(command, data)

    await verify_subscribe(1)

    mqtt_server.stop()
    await asyncio.sleep(0.1)
    assert not mqtt_client._client.is_connected

    mqtt_server.run()

    for i in range(_WAINTING_AFTER_RESTART):
        print(f"Wait for success reconnect... {i}/{_WAINTING_AFTER_RESTART}")
        if mqtt_client._client.is_connected:
            await verify_subscribe(2)
            return

        await asyncio.sleep(1)

    pytest.fail("Reconnect failed")


_test_MqttConnectionConfig_data = [
    ("cn", None, "mq.ecouser.net"),
    ("cn", "localhost", "localhost"),
    ("it", None, "mq-eu.ecouser.net"),
    ("it", "localhost", "localhost"),
]


@pytest.mark.parametrize("ssl", [None, False])
@pytest.mark.parametrize(
    "country,hostname,expected_hostname", _test_MqttConnectionConfig_data
)
def test_MqttConnectionConfig(
    ssl: None | bool,
    country: str,
    hostname: str | None,
    expected_hostname: str,
    session: ClientSession,
) -> None:
    args: dict = {
        "config": Configuration(
            session, device_id="test", country=country, continent="eu"
        )
    }
    if ssl is not None:
        args["ssl_context"] = ssl

    if hostname is not None:
        args["hostname"] = hostname

    mqtt = MqttConnectionConfig(**args)
    assert mqtt.hostname == expected_hostname
