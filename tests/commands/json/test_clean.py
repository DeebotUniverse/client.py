from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import Mock, patch

import pytest

from deebot_client.commands.json import GetCleanInfo
from deebot_client.commands.json.clean import (
    Clean,
    CleanArea,
    CleanAreaMower,
    CleanAreaV2,
    CleanMower,
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


@pytest.mark.parametrize("command_type", [Clean, CleanV2, CleanMower])
@pytest.mark.parametrize(
    ("action", "state", "expected"),
    [
        (CleanAction.START, None, CleanAction.START),
        (CleanAction.START, State.PAUSED, CleanAction.RESUME),
        (CleanAction.START, State.DOCKED, CleanAction.START),
        (CleanAction.PAUSE, None, CleanAction.PAUSE),
        (CleanAction.PAUSE, State.CLEANING, CleanAction.PAUSE),
        (CleanAction.PAUSE, State.PAUSED, CleanAction.PAUSE),
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
    posted = cast("Mock", authenticator.post_authenticated).call_args
    assert posted is not None
    assert posted.args[1]["cmdName"] == command.NAME

    if command_type is CleanV2:
        assert isinstance(command._args["content"], dict)
    if command_type is CleanMower:
        assert command.NAME == "clean"
        assert command._args["content"] == {"type": CleanMode.AUTO.value}


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
            CleanAreaV2(CleanMode.FREE_CLEAN, [5, 8]),
            {
                "act": "start",
                "content": {"type": "freeClean", "value": "1,5,8"},
            },
        ),
        (
            CleanAreaV2(CleanMode.FREE_CLEAN, [0], cleanings=2),
            {
                "act": "start",
                "content": {"type": "freeClean", "value": "2,0"},
            },
        ),
        (
            CleanV2(CleanAction.START),
            {"act": "start", "content": {"type": "auto"}},
        ),
        (
            CleanV2(CleanAction.PAUSE),
            {"act": "pause", "content": {"type": ""}},
        ),
        (
            CleanV2(CleanAction.RESUME),
            {"act": "resume", "content": {}},
        ),
        (
            CleanV2(CleanAction.STOP),
            {"act": "stop", "content": {"type": ""}},
        ),
        (
            CleanMower(CleanAction.START),
            {"act": "start", "content": {"type": "auto"}},
        ),
        (
            CleanMower(CleanAction.PAUSE),
            {"act": "pause", "content": {"type": "auto"}},
        ),
        (
            CleanMower(CleanAction.RESUME),
            {"act": "resume", "content": {"type": "auto"}},
        ),
        (
            CleanMower(CleanAction.STOP),
            {"act": "stop", "content": {"type": "auto"}},
        ),
        (
            CleanAreaMower(CleanMode.SPOT_AREA, [2]),
            {"act": "start", "content": {"type": "spotArea", "value": "2"}},
        ),
        (
            CleanAreaMower(CleanMode.SPOT_AREA, [2, 5]),
            {"act": "start", "content": {"type": "spotArea", "value": "2,5"}},
        ),
    ],
    ids=[
        "Rooms",
        "Rooms V2",
        "Coordinates",
        "Coordinates V2",
        "FreeClean",
        "FreeClean single room 2x",
        "CleanV2 start",
        "CleanV2 pause",
        "CleanV2 resume",
        "CleanV2 stop",
        "Mower auto start",
        "Mower auto pause",
        "Mower auto resume",
        "Mower auto stop",
        "Mower spot area",
        "Mower spot areas",
    ],
)
async def test_CleanArea(
    command: CleanArea | CleanAreaV2 | CleanMower | CleanAreaMower,
    args: dict[str, str],
) -> None:
    await assert_execute_command(command, args)


@pytest.mark.parametrize(
    ("action", "args"),
    [
        (CleanAction.PAUSE, {"act": "pause", "content": {"type": "spotArea"}}),
        (CleanAction.RESUME, {"act": "resume", "content": {"type": "spotArea"}}),
        (CleanAction.STOP, {"act": "stop", "content": {"type": "spotArea"}}),
    ],
)
def test_CleanAreaMower_keeps_type_without_value(
    action: CleanAction, args: dict[str, Any]
) -> None:
    command = CleanAreaMower(CleanMode.SPOT_AREA, [2])

    assert command.NAME == "clean"
    assert command._get_args(action) == args


@pytest.mark.parametrize("command_type", [CleanMower, Clean, CleanV2])
@pytest.mark.parametrize("action", list(CleanAction))
@pytest.mark.parametrize("code", [0, 20003])
async def test_clean_ack_refreshes_only_mower_activity(
    authenticator: Authenticator,
    api_device_info: ApiDeviceInfo,
    event_bus: EventBus,
    command_type: type[Clean],
    action: CleanAction,
    code: int,
) -> None:
    cast("Mock", authenticator.post_authenticated).return_value = {
        "ret": "ok",
        "resp": {"body": {"code": code}},
    }
    event_bus.notify(StateEvent(State.ERROR))
    with patch.object(event_bus, "request_refresh") as refresh:
        await command_type(action).execute(authenticator, api_device_info, event_bus)
        if command_type is CleanMower and code == 0:
            refresh.assert_called_once_with(StateEvent, queue_if_busy=True)
        else:
            refresh.assert_not_called()
        assert event_bus.get_last_event(StateEvent) == StateEvent(State.ERROR)


@pytest.mark.parametrize(
    ("state", "sent"),
    [(State.PAUSED, "resume"), (State.IDLE, "start"), (State.ERROR, "start")],
)
@pytest.mark.parametrize("code", [0, 20003])
async def test_mower_start_diagnostics_show_requested_and_sent_action(
    authenticator: Authenticator,
    api_device_info: ApiDeviceInfo,
    event_bus: EventBus,
    caplog: pytest.LogCaptureFixture,
    state: State,
    sent: str,
    code: int,
) -> None:
    """Distinguish HA's ambiguous paused label from the action actually sent."""
    cast("Mock", authenticator.post_authenticated).return_value = {
        "ret": "ok",
        "resp": {"body": {"code": code}},
    }
    event_bus.notify(StateEvent(state))
    await CleanMower(CleanAction.START).execute(
        authenticator, api_device_info, event_bus
    )
    posted = cast("Mock", authenticator.post_authenticated).call_args
    assert posted.args[1]["payload"]["body"]["data"] == {
        "act": sent,
        "content": {"type": "auto"},
    }
    assert (
        f"Mower clean request: action=start, cached_state={state.name}" in caplog.text
    )
    expected = "SUCCESS" if code == 0 else "FAILED"
    assert f"Mower clean result: sent_action={sent}, handling={expected}" in caplog.text
    # Diagnostics and an ACK must not pretend the mower changed its activity.
    assert event_bus.get_last_event(StateEvent) == StateEvent(state)
