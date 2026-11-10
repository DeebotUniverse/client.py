from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import orjson
import pytest

from deebot_client.commands.json import (
    GetMopAutoWashFrequency,
    SetMopAutoWashFrequency,
    SetWashInfo,
)
from deebot_client.events.mop_auto_wash_frequency import MopAutoWashFrequencyEvent
from deebot_client.events.wash_info import (
    MopAutoWashMode,
    MopAutoWashModeEvent,
    MopWashMode,
    MopWashModeEvent,
)
from tests.helpers import (
    get_request_json,
    get_success_body,
)

from . import assert_command, assert_set_command

if TYPE_CHECKING:
    from deebot_client.events import Event


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"interval": 10}, (MopAutoWashFrequencyEvent(10),)),
        ({"interval": 15}, (MopAutoWashFrequencyEvent(15),)),
        ({"interval": 25}, (MopAutoWashFrequencyEvent(25),)),
        (
            # T90 PRO (guaexd / twunby), firmware 1.103.0
            {
                "amount": 1,
                "dryMop": 0,
                "duration": 60,
                "interval": 15,
                "mode": 3,
                "wiseMode": 2,
            },
            (
                MopAutoWashFrequencyEvent(15),
                MopWashModeEvent(MopWashMode.INTELLIGENT_TEMPERATURE),
                MopAutoWashModeEvent(MopAutoWashMode.SMART),
            ),
        ),
        (
            {"interval": 10, "wiseMode": 0},
            (
                MopAutoWashFrequencyEvent(10),
                MopAutoWashModeEvent(MopAutoWashMode.BY_TIME),
            ),
        ),
        # Unknown enum values are ignored instead of failing the whole message
        (
            {"interval": 15, "mode": 99, "wiseMode": 99},
            (MopAutoWashFrequencyEvent(15),),
        ),
    ],
)
async def test_GetMopAutoWashFrequency(
    data: dict[str, Any], expected: tuple[Event, ...]
) -> None:
    json, firmware_event = get_request_json(get_success_body(data))
    await assert_command(GetMopAutoWashFrequency(), json, (firmware_event, *expected))


@pytest.mark.parametrize(("value"), [10, 15, 25])
async def test_SetMopAutoWashFrequency(value: int) -> None:
    command = SetMopAutoWashFrequency(value)
    args = {"interval": value}
    await assert_set_command(command, args, MopAutoWashFrequencyEvent(value))


@pytest.mark.parametrize(
    ("command", "args", "expected_events"),
    [
        (
            SetWashInfo(mode=MopWashMode.ECO),
            {"mode": 0},
            [MopWashModeEvent(MopWashMode.ECO)],
        ),
        (
            SetWashInfo(mode="deep"),
            {"mode": 2},
            [MopWashModeEvent(MopWashMode.DEEP)],
        ),
        (
            SetWashInfo(wise_mode=MopAutoWashMode.BY_ROOM),
            {"wiseMode": 1},
            [MopAutoWashModeEvent(MopAutoWashMode.BY_ROOM)],
        ),
        (
            SetWashInfo(wise_mode="smart"),
            {"wiseMode": 2},
            [MopAutoWashModeEvent(MopAutoWashMode.SMART)],
        ),
        (
            SetWashInfo(wise_mode=MopAutoWashMode.BY_TIME, interval=10),
            {"wiseMode": 0, "interval": 10},
            [
                MopAutoWashFrequencyEvent(10),
                MopAutoWashModeEvent(MopAutoWashMode.BY_TIME),
            ],
        ),
    ],
)
async def test_SetWashInfo(
    command: SetWashInfo, args: dict[str, Any], expected_events: list[Event]
) -> None:
    await assert_set_command(command, args, expected_events)


@pytest.mark.parametrize(
    ("command_values", "error", "error_message"),
    [
        (
            {},
            ValueError,
            "At least one of mode, wise_mode or interval must be provided.",
        ),
        (
            {"mode": "inexsting"},
            ValueError,
            "'INEXSTING' is not a valid MopWashMode member",
        ),
        (
            {"wise_mode": "inexsting"},
            ValueError,
            "'INEXSTING' is not a valid MopAutoWashMode member",
        ),
        (
            {"bla": "inexsting"},
            TypeError,
            re.escape(
                "SetWashInfo.__init__() got an unexpected keyword argument 'bla'"
            ),
        ),
    ],
)
def test_SetWashInfo_invalid(
    command_values: dict[str, Any], error: type[Exception], error_message: str
) -> None:
    with pytest.raises(error, match=error_message):
        SetWashInfo(**command_values)


@pytest.mark.parametrize(
    ("data", "expected_args"),
    [
        # Sent by the app when changing the wash method (no interval)
        ({"mode": 0}, {"mode": 0}),
        ({"wiseMode": 1, "interval": 10}, {"wiseMode": 1, "interval": 10}),
        ({"interval": 15}, {"interval": 15}),
    ],
)
def test_SetWashInfo_create_from_mqtt(
    data: dict[str, Any], expected_args: dict[str, Any]
) -> None:
    command = SetWashInfo.create_from_mqtt(orjson.dumps({"body": {"data": data}}))
    assert command._args == expected_args
