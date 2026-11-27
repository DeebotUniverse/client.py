from __future__ import annotations

import re
from typing import Any
from unittest.mock import Mock

import pytest

from deebot_client.commands.json.native_area import (
    NativeCleanRoom,
    NativeCleanZone,
    native_clean_area,
)
from deebot_client.event_bus import EventBus
from deebot_client.events import StateEvent
from deebot_client.models import CleanMode
from tests.commands.json import assert_command, assert_execute_command
from tests.helpers import get_request_json, get_success_body


def _verify_header(payload: dict[str, Any]) -> None:
    header = payload["header"]
    assert header["pri"] == 3
    assert header["m"] == "cloudctl"
    assert header["channel"] == "rop"
    assert header["ver"] == "0.0.1"
    assert header["tzm"] == 480
    assert isinstance(header["ts"], str)
    assert re.fullmatch(r"\d{13}", header["ts"]) is not None


@pytest.mark.parametrize(
    ("command", "name", "args"),
    [
        (
            NativeCleanRoom([1, 2]),
            "40007",
            {"cleanSwitch": True, "cleanMode": "area", "cleanValues": [1, 2]},
        ),
        (
            NativeCleanZone([-200, 100, -200, -50, 50, -50, 50, 100]),
            "40005",
            {
                "cleanSwitch": True,
                "cleanMode": "zone",
                "cleanValues": [-200, 100, -200, -50, 50, -50, 50, 100],
            },
        ),
    ],
)
async def test_native_area_wire_payload(
    command: NativeCleanRoom | NativeCleanZone, name: str, args: dict[str, Any]
) -> None:
    assert name == command.NAME
    payload = command._get_payload()
    assert isinstance(payload, dict)
    _verify_header(payload)
    assert payload["body"] == {"data": args}
    await assert_execute_command(command, args)


def test_native_clean_area_factory_room() -> None:
    cmd = native_clean_area(CleanMode.SPOT_AREA, [1, 2])
    assert isinstance(cmd, NativeCleanRoom)
    assert cmd.NAME == "40007"
    assert cmd._args == {
        "cleanSwitch": True,
        "cleanMode": "area",
        "cleanValues": [1, 2],
    }


@pytest.mark.parametrize(
    "area",
    [
        [-2000, 1000, 500, -500],
        [500, -500, -2000, 1000],
        [-2000, -500, 500, 1000],
        [500, 1000, -2000, -500],
    ],
)
def test_native_clean_area_factory_zone_corner_orders(area: list[int]) -> None:
    cmd = native_clean_area(CleanMode.CUSTOM_AREA, area)
    assert isinstance(cmd, NativeCleanZone)
    assert cmd.NAME == "40005"
    expected = [-200, 100, -200, -50, 50, -50, 50, 100]
    assert isinstance(cmd._args, dict)
    assert cmd._args["cleanValues"] == expected


def test_native_clean_area_factory_negative_coords() -> None:
    cmd = native_clean_area(CleanMode.CUSTOM_AREA, [-5000, -2000, -1000, -4000])
    assert isinstance(cmd, NativeCleanZone)
    expected = [-500, -200, -500, -400, -100, -400, -100, -200]
    assert isinstance(cmd._args, dict)
    assert cmd._args["cleanValues"] == expected


@pytest.mark.parametrize("cleanings", [0, 2, 3])
def test_native_clean_area_rejects_repetitions(cleanings: int) -> None:
    with pytest.raises(ValueError, match="Repetition count"):
        native_clean_area(CleanMode.SPOT_AREA, [1], cleanings=cleanings)


@pytest.mark.parametrize("mode", [CleanMode.AUTO, CleanMode.FREE_CLEAN])
def test_native_clean_area_unsupported_mode(mode: CleanMode) -> None:
    with pytest.raises(ValueError, match="not supported"):
        native_clean_area(mode, [1])


@pytest.mark.parametrize(
    ("invalid_rooms", "exc_type", "match_str"),
    [
        ([], ValueError, "cannot be empty"),
        ([True], TypeError, "non-boolean integer"),
        ([False], TypeError, "non-boolean integer"),
        ([1, "2"], TypeError, "non-boolean integer"),
        ([0], ValueError, "positive integer"),
        ([-1], ValueError, "positive integer"),
        ([1.5], TypeError, "non-boolean integer"),
    ],
)
def test_native_clean_room_invalid_inputs(
    invalid_rooms: Any, exc_type: type[Exception], match_str: str
) -> None:
    with pytest.raises(exc_type, match=match_str):
        NativeCleanRoom(invalid_rooms)


@pytest.mark.parametrize(
    ("invalid_zone", "exc_type", "match_str"),
    [
        ([1, 2, 3], ValueError, "requires exactly 8"),
        ([-200, 100, -200, -50, 50, -50, 50, True], TypeError, "non-boolean integer"),
        ([-200, 100, -200, -50, 50, -50, 50, "100"], TypeError, "non-boolean integer"),
        (
            [-200, 100, -200, -50, 50, -50, 50, 50],
            ValueError,
            "Coordinates do not match",
        ),
        (
            [50, 100, 50, -50, -200, -50, -200, 100],
            ValueError,
            "Degenerate zone rectangle",
        ),
        (
            [100, 100, 100, -50, 100, -50, 100, 100],
            ValueError,
            "Degenerate zone rectangle",
        ),
    ],
)
def test_native_clean_zone_invalid_inputs(
    invalid_zone: Any, exc_type: type[Exception], match_str: str
) -> None:
    with pytest.raises(exc_type, match=match_str):
        NativeCleanZone(invalid_zone)


@pytest.mark.parametrize(
    ("invalid_custom", "match_str"),
    [
        ([100, 200, 300], "exactly 4 diagonal coordinates"),
        ([100, 200, 300, 400, 500], "exactly 4 diagonal coordinates"),
        ([105, 200, 300, 400], "fractional centimeter"),
        ([float("nan"), 200, 300, 400], "must be finite"),
        ([float("inf"), 200, 300, 400], "must be finite"),
        ([100, 200, 100, 400], "Degenerate rectangle"),
        ([100, 200, 300, 200], "Degenerate rectangle"),
    ],
)
def test_native_clean_area_custom_invalid_geometry(
    invalid_custom: list[float], match_str: str
) -> None:
    with pytest.raises(ValueError, match=match_str):
        native_clean_area(CleanMode.CUSTOM_AREA, invalid_custom)


async def test_native_clean_area_no_invented_state_on_ack() -> None:
    cmd = NativeCleanRoom([1])
    event_bus = Mock(spec_set=EventBus)
    event_bus.get_last_event.return_value = None
    wrapped, firmware_event = get_request_json(get_success_body())
    await assert_command(cmd, wrapped, firmware_event)
    for call_item in event_bus.notify.call_args_list:
        assert not isinstance(call_item[0][0], StateEvent)
