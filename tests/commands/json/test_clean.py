from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest

from deebot_client.commands.json import GetCleanInfo
from deebot_client.commands.json.clean import (
    Clean,
    CleanArea,
    CleanAreaV2,
    CleanV2,
    GetCleanInfoV2,
)
from deebot_client.event_bus import EventBus
from deebot_client.events import FirmwareEvent, StateEvent
from deebot_client.models import ApiDeviceInfo, CleanAction, CleanMode, State
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_execute_command

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator


@pytest.mark.parametrize(
    ("command", "data", "expected"),
    [
        (
            GetCleanInfo,
            get_request_json(get_success_body({"trigger": "none", "state": "idle"})),
            StateEvent(State.IDLE),
        ),
        (
            GetCleanInfoV2,
            get_request_json(get_success_body({"trigger": "none", "state": "idle"})),
            StateEvent(State.IDLE),
        ),
        (
            GetCleanInfoV2,
            get_request_json(
                get_success_body(
                    {
                        "trigger": "none",
                        "state": "washing",
                        "cleanState": {
                            "cid": "122",
                            "router": "plan",
                            "motionState": "pause",
                            "content": {"subContent": {"type": "auto"}},
                            "cmode": 2,
                        },
                    }
                )
            ),
            StateEvent(State.PAUSED),
        ),
    ],
)
async def test_GetCleanInfo(
    command: type[GetCleanInfo],
    data: tuple[dict[str, Any], FirmwareEvent],
    expected: StateEvent,
) -> None:
    json, firmware_event = data
    await assert_command(command(), json, (firmware_event, expected))


@pytest.mark.parametrize("command_type", [Clean, CleanV2])
@pytest.mark.parametrize(
    ("action", "state", "expected"),
    [
        (CleanAction.START, None, CleanAction.START),
        (CleanAction.START, State.PAUSED, CleanAction.RESUME),
        (CleanAction.START, State.DOCKED, CleanAction.START),
        (CleanAction.RESUME, None, CleanAction.RESUME),
        (CleanAction.RESUME, State.PAUSED, CleanAction.RESUME),
        (CleanAction.RESUME, State.DOCKED, CleanAction.START),
        (CleanAction.STOP, None, CleanAction.STOP),
        (CleanAction.STOP, State.CLEANING, CleanAction.STOP),
        (CleanAction.STOP, State.PAUSED, CleanAction.STOP),
        (CleanAction.STOP, State.DOCKED, CleanAction.STOP),
    ],
)
async def test_Clean_act(
    authenticator: Authenticator,
    api_device_info: ApiDeviceInfo,
    command_type: type[Clean],
    action: CleanAction,
    state: State | None,
    expected: CleanAction,
) -> None:
    event_bus = Mock(spec_set=EventBus)
    event_bus.get_last_event.return_value = (
        StateEvent(state) if state is not None else None
    )
    command = command_type(action)

    await command.execute(authenticator, api_device_info, event_bus)

    assert isinstance(command._args, dict)
    assert command._args["act"] == expected.value

    if command_type is CleanV2:
        assert isinstance(command._args["content"], dict)


@pytest.mark.parametrize(
    ("command", "args"),
    [
        (
            CleanArea(CleanMode.SPOT_AREA, [5, 8]),
            {"act": "start", "type": "spotArea", "content": "5,8", "count": 1},
        ),
        (
            CleanAreaV2(CleanMode.SPOT_AREA, [5, 8]),
            {"act": "start", "content": {"type": "spotArea", "value": "5,8"}},
        ),
        (
            CleanArea(CleanMode.CUSTOM_AREA, [1580.0, -4087.0, 3833.0, -7525.0]),
            {
                "act": "start",
                "type": "customArea",
                "content": "1580.0,-4087.0,3833.0,-7525.0",
                "count": 1,
            },
        ),
        (
            CleanAreaV2(CleanMode.CUSTOM_AREA, [1580.0, -4087.0, 3833.0, -7525.0]),
            {
                "act": "start",
                "content": {
                    "type": "customArea",
                    "value": "1580.0,-4087.0,3833.0,-7525.0",
                },
            },
        ),
        (
            CleanAreaV2(CleanMode.FREE_CLEAN, [2]),
            {
                "act": "start",
                "content": {"type": "freeClean", "value": "1,2"},
            },
        ),
        (
            CleanAreaV2(CleanMode.FREE_CLEAN, [5, 8]),
            {
                "act": "start",
                "content": {"type": "freeClean", "value": "1,5;1,8"},
            },
        ),
        (
            CleanAreaV2(CleanMode.FREE_CLEAN, [0], 2),
            {
                "act": "start",
                "content": {"type": "freeClean", "value": "1,0"},
            },
        ),
        (
            CleanAreaV2(CleanMode.SPOT_AREA, [2, 5], free_clean=True),
            {
                "act": "start",
                "content": {"type": "freeClean", "value": "1,2;1,5"},
            },
        ),
        (
            CleanAreaV2(
                CleanMode.CUSTOM_AREA, [2201, 621, 4801, 3221], free_clean=True
            ),
            {
                "act": "start",
                "content": {"type": "freeClean", "value": "3,null,2201,621,4801,3221"},
            },
        ),
        (
            CleanAreaV2(
                CleanMode.CUSTOM_AREA,
                [-479, 2514, -1962, 1374, 1595, 2815, -120, 2215],
                free_clean=True,
            ),
            {
                "act": "start",
                "content": {
                    "type": "freeClean",
                    "value": "3,null,-479,2514,-1962,1374;3,null,1595,2815,-120,2215",
                },
            },
        ),
        (
            CleanAreaV2(
                CleanMode.CUSTOM_AREA,
                [1580.0, -4087.0, 3833.0, -7525.0],
                free_clean=True,
            ),
            {
                "act": "start",
                "content": {
                    "type": "freeClean",
                    "value": "3,null,1580,-4087,3833,-7525",
                },
            },
        ),
    ],
    ids=[
        "Rooms",
        "Rooms V2",
        "Coordinates",
        "Coordinates V2",
        "FreeClean single room",
        "FreeClean rooms",
        "FreeClean ignores cleanings",
        "FreeClean option rooms",
        "FreeClean option custom area",
        "FreeClean option two custom areas",
        "FreeClean option custom area floats",
    ],
)
async def test_CleanArea(
    command: CleanArea | CleanAreaV2, args: dict[str, str]
) -> None:
    await assert_execute_command(command, args)


@pytest.mark.parametrize(
    "area",
    [[], [1, 2, 3], [1, 2, 3, 4, 5]],
    ids=["empty", "3 coordinates", "5 coordinates"],
)
def test_CleanAreaV2_free_clean_invalid_custom_area(area: list[int | float]) -> None:
    with pytest.raises(ValueError, match="4 coordinates"):
        CleanAreaV2(CleanMode.CUSTOM_AREA, area, free_clean=True)


@pytest.mark.parametrize(
    ("mode", "free_clean"),
    [(CleanMode.SPOT_AREA, True), (CleanMode.FREE_CLEAN, False)],
    ids=["free_clean option", "FREE_CLEAN mode"],
)
def test_CleanAreaV2_free_clean_no_rooms(mode: CleanMode, *, free_clean: bool) -> None:
    with pytest.raises(ValueError, match="At least one room"):
        CleanAreaV2(mode, [], free_clean=free_clean)


def test_CleanAreaV2_free_clean_unsupported_mode() -> None:
    with pytest.raises(ValueError, match="does not support the auto mode"):
        CleanAreaV2(CleanMode.AUTO, [1], free_clean=True)
