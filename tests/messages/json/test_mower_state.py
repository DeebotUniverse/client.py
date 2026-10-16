from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from deebot_client.events import StateEvent
from deebot_client.message import HandlingState
from deebot_client.messages import get_message
from deebot_client.models import State

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus
    from deebot_client.models import StaticDeviceInfo


@pytest.mark.parametrize("device_class", ["300lc5"])
@pytest.mark.parametrize(
    "name", ["onCleanInfo", "onCleanInfo_V2", "onScheduleTaskInfo"]
)
@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"state": "clean", "cleanState": {"motionState": "working"}}, State.CLEANING),
        ({"state": "clean", "cleanState": {"motionState": "pause"}}, State.PAUSED),
        (
            {"state": "clean", "cleanState": {"motionState": "goCharging"}},
            State.RETURNING,
        ),
        ({"state": "goCharging"}, State.RETURNING),
        ({"state": "idle"}, State.IDLE),
        (
            {
                "trigger": "alert",
                "state": "clean",
                "cleanState": {"motionState": "working"},
            },
            State.ERROR,
        ),
    ],
)
async def test_mower_activity_push(
    static_device_info: StaticDeviceInfo,
    event_bus: EventBus,
    name: str,
    data: dict[str, Any],
    expected: State,
) -> None:
    handler = get_message(name, static_device_info)
    assert handler is not None
    event_bus.notify(StateEvent(State.ERROR))
    result = handler.handle(event_bus, {"body": {"data": data}})
    assert result.state is HandlingState.SUCCESS
    assert event_bus.get_last_event(StateEvent) == StateEvent(expected)


@pytest.mark.parametrize("device_class", ["300lc5"])
@pytest.mark.parametrize(
    ("data", "expected", "refresh", "handled"),
    [
        ({"trigger": "app", "state": "goCharging"}, State.RETURNING, False, True),
        ({"trigger": "workComplete", "state": "idle"}, State.RETURNING, True, True),
        ({"trigger": "alert", "state": "idle"}, State.ERROR, False, True),
        ({"state": "unknown"}, State.RETURNING, False, False),
    ],
)
async def test_mower_charge_push(
    static_device_info: StaticDeviceInfo,
    event_bus: EventBus,
    data: dict[str, Any],
    expected: State,
    refresh: bool,
    handled: bool,
) -> None:
    handler = get_message("onChargeInfo", static_device_info)
    assert handler is not None
    event_bus.notify(StateEvent(State.RETURNING))
    with patch.object(event_bus, "request_refresh") as request_refresh:
        result = handler.handle(event_bus, {"body": {"data": data}})
        assert event_bus.get_last_event(StateEvent) == StateEvent(expected)
        if refresh:
            request_refresh.assert_called_once_with(StateEvent, queue_if_busy=True)
        else:
            request_refresh.assert_not_called()
    expected_result = HandlingState.SUCCESS if handled else HandlingState.ANALYSE_LOGGED
    assert result.state is expected_result


@pytest.mark.parametrize("name", ["onChargeInfo", "onScheduleTaskInfo"])
async def test_mower_push_does_not_change_vacuum_activity(
    static_device_info: StaticDeviceInfo, event_bus: EventBus, name: str
) -> None:
    handler = get_message(name, static_device_info)
    assert handler is not None
    event_bus.notify(StateEvent(State.DOCKED))
    with patch.object(event_bus, "request_refresh") as request_refresh:
        result = handler.handle(
            event_bus,
            {
                "body": {
                    "data": {"state": "clean", "cleanState": {"motionState": "working"}}
                }
            },
        )
        assert result.state is HandlingState.ANALYSE_LOGGED
        assert event_bus.get_last_event(StateEvent) == StateEvent(State.DOCKED)
        request_refresh.assert_not_called()


@pytest.mark.parametrize("name", ["getCleanInfo", "offCleanInfo", "reportCleanInfo"])
async def test_clean_info_legacy_names_still_work(
    static_device_info: StaticDeviceInfo, event_bus: EventBus, name: str
) -> None:
    handler = get_message(name, static_device_info)
    assert handler is not None
    result = handler.handle(
        event_bus,
        {
            "body": {
                "data": {"state": "clean", "cleanState": {"motionState": "working"}}
            }
        },
    )
    assert result.state is HandlingState.SUCCESS
    assert event_bus.get_last_event(StateEvent) == StateEvent(State.CLEANING)
