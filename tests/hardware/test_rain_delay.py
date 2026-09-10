from __future__ import annotations

from deebot_client.commands.json import COMMANDS, SetRainDelay
from deebot_client.events import RainDelayEvent
from deebot_client.hardware import get_static_device_info
from deebot_client.messages import get_message
from deebot_client.messages.json import OnRainDelay


async def test_rain_delay_capability() -> None:
    device_info = await get_static_device_info("2i0fns")
    assert device_info is not None

    capability = device_info.capabilities.settings.rain_delay
    assert capability is not None
    assert capability.event is RainDelayEvent
    assert capability.get == []
    assert capability.set is SetRainDelay
    assert device_info.capabilities.get_refresh_commands(RainDelayEvent) == []


async def test_rain_delay_registration() -> None:
    device_info = await get_static_device_info("2i0fns")
    assert device_info is not None

    assert COMMANDS[SetRainDelay.NAME] is SetRainDelay
    assert get_message(OnRainDelay.NAME, device_info) is OnRainDelay
