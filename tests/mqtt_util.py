"""Utilities for testing MQTT."""
from __future__ import annotations

import asyncio
import datetime
import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, Mock

from deebot_client.event_bus import EventBus
from deebot_client.mqtt_client import MqttClient, SubscriberInfo

if TYPE_CHECKING:
    from collections.abc import Callable

    from aiomqtt import Client

    from deebot_client.models import ApiDeviceInfo


async def verify_subscribe(
    test_client: Client,
    device_info: ApiDeviceInfo,
    mock: Mock,
    *,
    expected_called: bool,
) -> None:
    command = "test"
    data = json.dumps({"test": str(datetime.datetime.now())}).encode("utf-8")
    topic = f"iot/atr/{command}/{device_info['did']}/{device_info['class']}/{device_info['resource']}/j"
    await test_client.publish(topic, data)

    await asyncio.sleep(0.1)
    if expected_called:
        mock.assert_called_with(command, data)
    else:
        mock.assert_not_called()

    mock.reset_mock()


async def subscribe(
    mqtt_client: MqttClient, device_info: ApiDeviceInfo
) -> tuple[Mock, Mock, Callable[[], None]]:
    events = Mock(spec=EventBus)
    callback = MagicMock()
    unsubscribe = await mqtt_client.subscribe(
        SubscriberInfo(device_info, events, callback)
    )
    await asyncio.sleep(0.1)
    return (events, callback, unsubscribe)
