from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from deebot_client.commands.ngiot.clean import Clean, CleanArea, map_live_state, map_snapshot_state
from deebot_client.exceptions import ApiError
from deebot_client.models import CleanAction, CleanMode, State
from deebot_client.ngiot_client import (
    APN_AREA_CLEAN,
    APN_CLEAN_START,
    APN_PAUSE,
    APN_RESUME,
    APN_RETURN_TO_DOCK,
)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"workMode": "smart", "pauseSwitch": True}, State.PAUSED),
        ({"workMode": "goCharge"}, State.RETURNING),
        ({"workMode": "idle", "chargeStatus": True}, State.DOCKED),
        ({"workMode": "smart", "chargeStatus": False}, State.CLEANING),
        ({"workMode": "unknown"}, State.IDLE),
    ],
)
def test_map_snapshot_state(payload: dict[str, object], expected: State) -> None:
    assert map_snapshot_state(payload) is expected


@pytest.mark.parametrize(
    ("payload", "previous", "expected"),
    [
        ({"status": "smartclean", "pauseSwitch": True}, None, State.PAUSED),
        ({"status": "smartclean", "pauseSwitch": False}, None, State.CLEANING),
        ({"status": "idle", "chargeStatus": True}, None, State.DOCKED),
        ({"pauseSwitch": False}, State.PAUSED, State.CLEANING),
        ({"workMode": "goCharge"}, None, State.RETURNING),
        ({"status": "unknown"}, None, None),
    ],
)
def test_map_live_state(
    payload: dict[str, object], previous: State | None, expected: State | None
) -> None:
    assert map_live_state(payload, previous=previous) is expected


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        (CleanAction.START, (APN_CLEAN_START, {"cleanSwitch": True, "cleanMode": "smart"})),
        (CleanAction.PAUSE, (APN_PAUSE, {"pauseSwitch": True})),
        (CleanAction.RESUME, (APN_RESUME, {"pauseSwitch": False})),
        (CleanAction.STOP, (APN_RETURN_TO_DOCK, {"chargeSwitch": True})),
    ],
)
def test_clean_get_request(action: CleanAction, expected: tuple[str, dict[str, object]]) -> None:
    assert Clean(action)._get_request() == expected


@pytest.mark.asyncio
async def test_clean_area_requires_supported_mode() -> None:
    command = CleanArea(CleanMode.AUTO, [1])
    with pytest.raises(ApiError, match="room-id cleaning only"):
        await command._request_ngiot(None, None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_clean_area_requires_single_cleaning() -> None:
    command = CleanArea(CleanMode.SPOT_AREA, [1], cleanings=2)
    with pytest.raises(ApiError, match="repeat count"):
        await command._request_ngiot(None, None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_clean_area_builds_area_request() -> None:
    client = type("Client", (), {"request": AsyncMock(return_value={"body": {}})})()
    command = CleanArea(CleanMode.SPOT_AREA, [1, 2])

    await command._request_ngiot(client, None)  # type: ignore[arg-type]

    client.request.assert_awaited_once_with(
        None,
        apn=APN_AREA_CLEAN,
        body_data={"cleanSwitch": True, "cleanMode": "area", "cleanValues": [1, 2]},
    )
