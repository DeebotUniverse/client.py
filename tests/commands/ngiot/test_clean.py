from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from deebot_client.commands.ngiot.clean import (
    Clean,
    CleanArea,
    GetCleanInfo,
    map_live_state,
    map_snapshot_state,
)
from deebot_client.commands.ngiot.common import (
    APN_AREA_CLEAN,
    APN_CLEAN_START,
    APN_PAUSE,
    APN_RESUME,
    APN_RETURN_TO_DOCK,
)
from deebot_client.event_bus import EventBus
from deebot_client.events import StateEvent
from deebot_client.exceptions import ApiError
from deebot_client.message import HandlingState
from deebot_client.models import CleanAction, CleanMode, State
from deebot_client.ngiot_client import NgiotRequest


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"workMode": "auto_pause", "pauseSwitch": True}, State.PAUSED),
        ({"workMode": "goCharge"}, State.RETURNING),
        ({"workMode": "stop", "chargeStatus": True}, State.DOCKED),
        ({"workMode": "smart"}, State.CLEANING),
        ({"workMode": "stop", "chargeStatus": False}, State.IDLE),
    ],
)
def test_map_snapshot_state(data: dict[str, Any], expected: State) -> None:
    assert map_snapshot_state(data) is expected


@pytest.mark.parametrize(
    ("data", "previous", "expected"),
    [
        ({"status": "smartClean", "pauseSwitch": False}, None, State.CLEANING),
        ({"status": "smartClean", "pauseSwitch": True}, None, State.PAUSED),
        ({"status": "goCharge"}, None, State.RETURNING),
        ({"status": "idle", "chargeStatus": True}, None, State.DOCKED),
        ({"pauseSwitch": True}, State.CLEANING, State.PAUSED),
        ({"pauseSwitch": False}, State.PAUSED, State.CLEANING),
        ({"unknown": True}, None, None),
    ],
)
def test_map_live_state(
    data: dict[str, Any],
    previous: State | None,
    expected: State | None,
) -> None:
    assert map_live_state(data, previous) is expected


@pytest.mark.parametrize(
    ("action", "expected_apn", "expected_body"),
    [
        (
            CleanAction.START,
            APN_CLEAN_START,
            {"cleanSwitch": True, "cleanMode": "smart"},
        ),
        (CleanAction.PAUSE, APN_PAUSE, {"pauseSwitch": True}),
        (CleanAction.RESUME, APN_RESUME, {"pauseSwitch": False}),
        (CleanAction.STOP, APN_RETURN_TO_DOCK, {"chargeSwitch": True}),
    ],
)
def test_clean_get_request(
    action: CleanAction,
    expected_apn: str,
    expected_body: dict[str, Any],
) -> None:
    assert Clean(action)._get_request() == (expected_apn, expected_body)


async def test_clean_request_uses_action_request() -> None:
    client = AsyncMock()
    client.request.return_value = {"body": {"code": 0, "msg": "ok"}}
    device_info: dict[str, Any] = {
        "did": "did-1",
        "class": "eyfj07",
        "resource": "res-1",
    }

    response = await Clean(CleanAction.PAUSE)._request_ngiot(client, device_info)

    assert response == {"body": {"code": 0, "msg": "ok"}}
    client.request.assert_awaited_once_with(
        device_info,
        NgiotRequest(apn=APN_PAUSE, body_data={"pauseSwitch": True}),
    )


async def test_clean_area_uses_room_ids() -> None:
    client = AsyncMock()
    client.request.return_value = {"body": {"code": 0, "msg": "ok"}}
    device_info: dict[str, Any] = {
        "did": "did-1",
        "class": "eyfj07",
        "resource": "res-1",
    }

    response = await CleanArea(CleanMode.SPOT_AREA, [2, 5.0])._request_ngiot(
        client,
        device_info,
    )

    assert response == {"body": {"code": 0, "msg": "ok"}}
    client.request.assert_awaited_once_with(
        device_info,
        NgiotRequest(
            apn=APN_AREA_CLEAN,
            body_data={
                "cleanSwitch": True,
                "cleanMode": "area",
                "cleanValues": [2, 5],
            },
        ),
    )


@pytest.mark.parametrize(
    "command",
    [
        CleanArea(CleanMode.CUSTOM_AREA, [1, 2, 3, 4]),
        CleanArea(CleanMode.SPOT_AREA, [1], cleanings=2),
    ],
)
async def test_clean_area_rejects_uncaptured_shapes(command: CleanArea) -> None:
    with pytest.raises(ApiError):
        await command._request_ngiot(AsyncMock(), {"class": "eyfj07"})


def test_get_clean_info_handles_snapshot_state() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetCleanInfo.handle(
        event_bus,
        {"body": {"data": {"workMode": "smart", "chargeStatus": False}}},
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(StateEvent(State.CLEANING))
