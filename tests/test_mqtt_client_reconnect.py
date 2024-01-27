from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from aiomqtt import Client
import pytest

from .fixtures.mqtt_server import MqttServer
from .mqtt_util import subscribe, verify_subscribe

if TYPE_CHECKING:
    from collections.abc import Generator

    from deebot_client.models import DeviceInfo, MqttConfiguration
    from deebot_client.mqtt_client import MqttClient

_WAITING_AFTER_RESTART = 30


@pytest.fixture
def mqtt_server() -> Generator[MqttServer, None, None]:
    server = MqttServer()
    server.config.options["ports"] = {"1883/tcp": 54321}
    server.run()
    yield server
    server.stop()


@pytest.mark.timeout(_WAITING_AFTER_RESTART + 10)
async def test_client_reconnect_on_broker_error(
    mqtt_client: MqttClient,
    mqtt_server: MqttServer,
    device_info: DeviceInfo,
    mqtt_config: MqttConfiguration,
    caplog: pytest.LogCaptureFixture,
) -> None:
    (_, callback, _) = await subscribe(mqtt_client, device_info)
    async with Client(
        hostname=mqtt_config.hostname,
        port=mqtt_config.port,
        identifier="Test-helper",
        tls_context=mqtt_config.ssl_context,
    ) as client:
        # test client cannot be used as we restart the broker in this test
        await verify_subscribe(client, device_info, callback, expected_called=True)

    caplog.clear()
    mqtt_server.stop()
    await asyncio.sleep(0.1)

    assert (
        "deebot_client.mqtt_client",
        logging.WARNING,
        "Connection lost; Reconnecting in 5 seconds ...",
    ) in caplog.record_tuples
    caplog.clear()

    mqtt_server.run()

    expected_log_tuple = (
        "deebot_client.mqtt_client",
        logging.DEBUG,
        "All mqtt tasks created",
    )
    for i in range(_WAITING_AFTER_RESTART):
        print(f"Wait for success reconnect... {i}/{_WAITING_AFTER_RESTART}")
        if expected_log_tuple in caplog.record_tuples:
            async with Client(
                hostname=mqtt_config.hostname,
                port=mqtt_config.port,
                identifier="Test-helper",
                tls_context=mqtt_config.ssl_context,
            ) as client:
                # test client cannot be used as we restart the broker in this test
                await verify_subscribe(
                    client, device_info, callback, expected_called=True
                )
            return

        await asyncio.sleep(1)

    pytest.fail("Reconnect failed")
