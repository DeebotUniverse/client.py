from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from deebot_client.command import Command
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import CleanAreaV2, CleanV2
from deebot_client.commands.json.work_state import GetWorkState
from deebot_client.events import StateEvent
from deebot_client.hardware.b7vftn import get_device_info
from deebot_client.models import CleanAction, CleanMode, State


def test_b7vftn_uses_clean_v2() -> None:
    capabilities = get_device_info().capabilities

    assert capabilities.clean.action.command is CleanV2
    assert capabilities.state.get == [GetChargeState(), GetWorkState()]
    assert capabilities.station is not None
    assert capabilities.station.state.get == [GetWorkState()]
    assert CleanV2(CleanAction.STOP)._args == {"act": "stop", "content": {"type": ""}}


@pytest.mark.parametrize(
    ("rooms", "value"),
    [
        ([15], "1,15"),
        ([1, 15], "1,1;1,15"),
        ([5.0], "1,5"),
    ],
)
def test_b7vftn_rooms_use_free_clean(rooms: list[int | float], value: str) -> None:
    area = get_device_info().capabilities.clean.action.area
    assert area is not None

    command = area(CleanMode.SPOT_AREA, rooms, 2)

    assert command.NAME == "clean_V2"
    assert command._args == {
        "act": "start",
        "content": {"type": "freeClean", "value": value},
    }


def test_b7vftn_custom_area_uses_clean_area_v2() -> None:
    area = get_device_info().capabilities.clean.action.area
    assert area is not None

    command = area(CleanMode.CUSTOM_AREA, [1, 2, 3, 4], 1)

    assert isinstance(command, CleanAreaV2)


async def test_b7vftn_room_clean_starts_while_paused() -> None:
    area = get_device_info().capabilities.clean.action.area
    assert area is not None
    command = area(CleanMode.SPOT_AREA, [15], 1)
    event_bus = Mock()
    event_bus.get_last_event.return_value = StateEvent(State.PAUSED)
    sent: list[dict[str, Any]] = []

    async def _execute(self: Command, *_: Any) -> tuple[Any, dict[str, Any]]:
        sent.append(self._args)
        return Mock(), {}

    with patch.object(Command, "_execute", _execute):
        await command._execute(AsyncMock(), Mock(), event_bus)

    assert sent == [{"act": "start", "content": {"type": "freeClean", "value": "1,15"}}]
