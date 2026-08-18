"""Tests for DEEBOT NEO 2.0 commands (neo2.py)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from deebot_client.authentication import Authenticator
from deebot_client.commands.json.neo2 import (
    GetCombinedStatus,
    Neo2Charge,
    Neo2Clean,
    Neo2SetFanSpeed,
    _get_sst,
    _ngiot_post,
)
from deebot_client.event_bus import EventBus
from deebot_client.events import BatteryEvent, ErrorEvent, FanSpeedEvent, LifeSpanEvent, StateEvent
from deebot_client.events.fan_speed import FanSpeedLevel
from deebot_client.events.water_info import MopAttachedEvent, WaterAmount, WaterAmountEvent
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import ApiDeviceInfo, CleanAction, Credentials, LifeSpan, State
from tests.helpers import get_request_json, get_success_body


_DEVICE_INFO = ApiDeviceInfo(
    {
        "company": "company",
        "did": "test_did",
        "name": "DEEBOT NEO 2.0",
        "nick": "neo2",
        "resource": "test_res",
        "class": "eyfj07",
    }
)

_CREDENTIALS = Credentials("test_token", "test_user_id", 9999)


@pytest.fixture(autouse=True)
def clear_combined_status_cache() -> None:
    GetCombinedStatus._cache.clear()


def _make_authenticator(response: dict[str, Any]) -> Mock:
    auth = Mock(spec_set=Authenticator)
    auth.authenticate = AsyncMock(return_value=_CREDENTIALS)
    auth.post_authenticated = AsyncMock(return_value=response)
    return auth


# ---------------------------------------------------------------------------
# GetCombinedStatus
# ---------------------------------------------------------------------------


async def test_get_combined_status_docked() -> None:
    data = {
        "battery": 100,
        "chargeStatus": True,
        "pauseSwitch": False,
        "error": [0],
        "fanMode": "max",
        "waterMode": "low",
        "mopState": "none",
        "workMode": "stop",
        "consumables": [
            {"type": "sideBrush", "left": 6000, "total": 12000},
            {"type": "rollBrush", "left": 9000, "total": 12000},
        ],
    }
    response, _ = get_request_json(get_success_body(data=data))
    auth = _make_authenticator(response)
    event_bus = Mock(spec_set=EventBus)

    await GetCombinedStatus().execute(auth, _DEVICE_INFO, event_bus)

    calls = [c.args[0] for c in event_bus.notify.call_args_list]
    assert BatteryEvent(100) in calls
    assert StateEvent(State.DOCKED) in calls
    assert FanSpeedEvent(FanSpeedLevel.MAX_PLUS) in calls
    assert WaterAmountEvent(WaterAmount.LOW) in calls
    assert MopAttachedEvent(attached=False) in calls
    assert ErrorEvent(code=0, description="No error") in calls
    assert LifeSpanEvent(type=LifeSpan.SIDE_BRUSH, percent=50.0, remaining=6000) in calls
    assert LifeSpanEvent(type=LifeSpan.BRUSH, percent=75.0, remaining=9000) in calls


async def test_get_combined_status_cleaning() -> None:
    data = {
        "battery": 80,
        "chargeStatus": False,
        "pauseSwitch": False,
        "workMode": "auto",
        "error": [0],
    }
    response, _ = get_request_json(get_success_body(data=data))
    auth = _make_authenticator(response)
    event_bus = Mock(spec_set=EventBus)

    await GetCombinedStatus().execute(auth, _DEVICE_INFO, event_bus)

    calls = [c.args[0] for c in event_bus.notify.call_args_list]
    assert StateEvent(State.CLEANING) in calls
    assert BatteryEvent(80) in calls


async def test_get_combined_status_paused() -> None:
    data = {
        "battery": 75,
        "chargeStatus": False,
        "pauseSwitch": True,
        "workMode": "auto",
        "error": [0],
    }
    response, _ = get_request_json(get_success_body(data=data))
    auth = _make_authenticator(response)
    event_bus = Mock(spec_set=EventBus)

    await GetCombinedStatus().execute(auth, _DEVICE_INFO, event_bus)

    calls = [c.args[0] for c in event_bus.notify.call_args_list]
    assert StateEvent(State.PAUSED) in calls


async def test_get_combined_status_idle() -> None:
    data = {
        "battery": 100,
        "chargeStatus": False,
        "pauseSwitch": False,
        "workMode": "stop",
        "error": [0],
    }
    response, _ = get_request_json(get_success_body(data=data))
    auth = _make_authenticator(response)
    event_bus = Mock(spec_set=EventBus)

    await GetCombinedStatus().execute(auth, _DEVICE_INFO, event_bus)

    calls = [c.args[0] for c in event_bus.notify.call_args_list]
    assert StateEvent(State.IDLE) in calls


async def test_get_combined_status_cache() -> None:
    data = {"battery": 99, "chargeStatus": True, "error": [0]}
    response, _ = get_request_json(get_success_body(data=data))
    auth = _make_authenticator(response)
    event_bus = Mock(spec_set=EventBus)

    await GetCombinedStatus().execute(auth, _DEVICE_INFO, event_bus)
    await GetCombinedStatus().execute(auth, _DEVICE_INFO, event_bus)

    # Second call should hit cache — post_authenticated called only once
    assert auth.post_authenticated.call_count == 1


async def test_get_combined_status_no_data() -> None:
    response, _ = get_request_json(get_success_body())
    auth = _make_authenticator(response)
    event_bus = Mock(spec_set=EventBus)

    await GetCombinedStatus().execute(auth, _DEVICE_INFO, event_bus)

    # body.data is None — should ANALYSE, no events beyond possible firmware
    state_calls = [
        c for c in event_bus.notify.call_args_list if isinstance(c.args[0], StateEvent)
    ]
    assert len(state_calls) == 0


# ---------------------------------------------------------------------------
# Neo2Charge
# ---------------------------------------------------------------------------


async def test_Neo2Charge_success() -> None:
    auth = _make_authenticator({"ret": "ok"})
    event_bus = Mock(spec_set=EventBus)

    result = await Neo2Charge().execute(auth, _DEVICE_INFO, event_bus)

    assert result.device_reached is True
    event_bus.notify.assert_called_once_with(StateEvent(State.RETURNING))
    auth.post_authenticated.assert_called_once()
    path = auth.post_authenticated.call_args[0][0]
    assert path == "appsvr/app.do"


async def test_Neo2Charge_failed() -> None:
    auth = _make_authenticator({"ret": "fail", "errno": 500})
    event_bus = Mock(spec_set=EventBus)

    result = await Neo2Charge().execute(auth, _DEVICE_INFO, event_bus)

    assert result.device_reached is False
    event_bus.notify.assert_not_called()


# ---------------------------------------------------------------------------
# Neo2Clean
# ---------------------------------------------------------------------------


async def test_Neo2Clean_start() -> None:
    auth = _make_authenticator({"ret": "ok"})
    event_bus = Mock(spec_set=EventBus)

    result = await Neo2Clean(CleanAction.START).execute(auth, _DEVICE_INFO, event_bus)

    assert result.device_reached is True
    event_bus.notify.assert_called_once_with(StateEvent(State.CLEANING))
    path = auth.post_authenticated.call_args[0][0]
    assert path == "appsvr/app.do"


@pytest.mark.parametrize(
    ("action", "apn", "body_data", "expected_state"),
    [
        (CleanAction.PAUSE, "40009", {"pauseSwitch": True}, StateEvent(State.PAUSED)),
        (CleanAction.STOP, "40009", {"pauseSwitch": True}, StateEvent(State.PAUSED)),
        (CleanAction.RESUME, "40011", {"pauseSwitch": False}, StateEvent(State.CLEANING)),
    ],
    ids=["pause", "stop", "resume"],
)
async def test_Neo2Clean_ngiot(
    action: CleanAction,
    apn: str,
    body_data: dict[str, Any],
    expected_state: StateEvent,
) -> None:
    auth = Mock(spec_set=Authenticator)
    auth.authenticate = AsyncMock(return_value=_CREDENTIALS)
    event_bus = Mock(spec_set=EventBus)

    with (
        patch("deebot_client.commands.json.neo2.aiohttp.ClientSession") as mock_cs,
        patch(
            "deebot_client.commands.json.neo2._get_sst",
            new=AsyncMock(return_value="test_sst"),
        ) as mock_sst,
        patch(
            "deebot_client.commands.json.neo2._ngiot_post",
            new=AsyncMock(return_value={}),
        ) as mock_post,
    ):
        mock_session = AsyncMock()
        mock_cs.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cs.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await Neo2Clean(action).execute(auth, _DEVICE_INFO, event_bus)

    assert result.device_reached is True
    event_bus.notify.assert_called_once_with(expected_state)
    mock_sst.assert_called_once_with(
        mock_session,
        token="test_token",
        user_id="test_user_id",
        did="test_did",
        mid="eyfj07",
    )
    mock_post.assert_called_once_with(
        mock_session,
        sst="test_sst",
        eid="test_did",
        et="eyfj07",
        er="test_res",
        apn=apn,
        body_data=body_data,
    )


# ---------------------------------------------------------------------------
# Neo2SetFanSpeed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("level", "expected_mode"),
    [
        (FanSpeedLevel.QUIET, "quiet"),
        (FanSpeedLevel.NORMAL, "standard"),
        (FanSpeedLevel.MAX, "strong"),
        (FanSpeedLevel.MAX_PLUS, "max"),
    ],
    ids=["quiet", "normal", "max", "max_plus"],
)
async def test_Neo2SetFanSpeed(level: FanSpeedLevel, expected_mode: str) -> None:
    auth = Mock(spec_set=Authenticator)
    auth.authenticate = AsyncMock(return_value=_CREDENTIALS)
    event_bus = Mock(spec_set=EventBus)

    with (
        patch("deebot_client.commands.json.neo2.aiohttp.ClientSession") as mock_cs,
        patch(
            "deebot_client.commands.json.neo2._get_sst",
            new=AsyncMock(return_value="test_sst"),
        ),
        patch(
            "deebot_client.commands.json.neo2._ngiot_post",
            new=AsyncMock(return_value={}),
        ) as mock_post,
    ):
        mock_session = AsyncMock()
        mock_cs.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cs.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await Neo2SetFanSpeed(level).execute(auth, _DEVICE_INFO, event_bus)

    assert result.device_reached is True
    event_bus.notify.assert_called_once_with(FanSpeedEvent(level))
    mock_post.assert_called_once_with(
        mock_session,
        sst="test_sst",
        eid="test_did",
        et="eyfj07",
        er="test_res",
        apn="50011",
        body_data={"fanMode": expected_mode},
    )


async def test_Neo2SetFanSpeed_from_string() -> None:
    cmd = Neo2SetFanSpeed("max")
    assert cmd._speed == FanSpeedLevel.MAX_PLUS
