from __future__ import annotations

from unittest.mock import Mock

import orjson
import pytest

from deebot_client.commands.json import SetRainDelay
from deebot_client.event_bus import EventBus
from tests.commands.json import assert_execute_command


@pytest.mark.parametrize(
    ("enabled", "delay"),
    [
        (False, 180),
        (True, 0),
        (True, 30),
        (True, 180),
        (True, 300),
    ],
)
async def test_set_rain_delay(enabled: bool, delay: int) -> None:
    command = SetRainDelay(enabled, delay)
    args = {"enable": 1 if enabled else 0, "delay": delay}

    await assert_execute_command(command, args)
    assert command._get_payload()["body"] == {"data": args}
    assert command.create_from_mqtt(orjson.dumps({"body": {"data": args}})) == command

    event_bus = Mock(spec_set=EventBus)
    command.handle_mqtt_p2p(event_bus, orjson.dumps({"body": {"code": 0, "msg": "ok"}}))
    event_bus.notify.assert_not_called()


@pytest.mark.parametrize("delay", [-1, 1, 15, 301])
def test_set_rain_delay_rejects_unsupported_delay(delay: int) -> None:
    with pytest.raises(ValueError, match=f"Unsupported rain delay: {delay}"):
        SetRainDelay(True, delay)
