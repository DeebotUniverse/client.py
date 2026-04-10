from __future__ import annotations

from unittest.mock import Mock, patch

from deebot_client.event_bus import EventBus
from deebot_client.events import StateEvent
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.messages import get_message
from deebot_client.messages.json.ngiot import OnNgiotMapEvent, OnNgiotStatusEvent
from deebot_client.models import State


def test_get_message_resolves_ngiot_numeric_topics() -> None:
    from deebot_client.const import DataType

    assert get_message("10000", DataType.JSON) is OnNgiotStatusEvent
    assert get_message("30000", DataType.JSON) is OnNgiotMapEvent


def test_on_ngiot_map_event_dispatches_major_and_trace_handlers() -> None:
    event_bus = Mock(spec_set=EventBus)
    payload = {"body": {"data": {"mapData": {}, "mapTraceData": {}}}}

    with (
        patch(
            "deebot_client.messages.json.ngiot.GetMajorMap._handle_body_data_dict",
            return_value=HandlingResult.success(),
        ) as handle_major,
        patch(
            "deebot_client.messages.json.ngiot.GetMapTrace._handle_body_data_dict",
            return_value=HandlingResult.success(),
        ) as handle_trace,
    ):
        result = OnNgiotMapEvent.handle(event_bus, payload)

    assert result.state == HandlingState.SUCCESS
    handle_major.assert_called_once_with(event_bus, payload["body"]["data"])
    handle_trace.assert_called_once_with(event_bus, payload["body"]["data"])


def test_on_ngiot_map_event_dispatches_pos_only_handler() -> None:
    event_bus = Mock(spec_set=EventBus)
    payload = {"body": {"data": {"pos": {}}}}

    with patch(
        "deebot_client.messages.json.ngiot.GetPos._handle_body_data_dict",
        return_value=HandlingResult.success(),
    ) as handle_pos:
        result = OnNgiotMapEvent.handle(event_bus, payload)

    assert result.state == HandlingState.SUCCESS
    handle_pos.assert_called_once_with(event_bus, payload["body"]["data"])


def test_on_ngiot_map_event_accepts_minor_only_payload() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = OnNgiotMapEvent.handle(
        event_bus,
        {"body": {"data": {"mapMinorData": {"piece": 1}}}},
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_not_called()


def test_on_ngiot_status_event_dispatches_live_state() -> None:
    event_bus = Mock(spec_set=EventBus)
    event_bus.get_last_event.return_value = StateEvent(State.PAUSED)
    payload = {
        "body": {
            "data": {
                "battery": 81,
                "cleanArea": 15,
                "cleanTime": 12,
                "childLock": True,
                "volume": 4,
                "status": "smartclean",
                "pauseSwitch": False,
            }
        }
    }

    with (
        patch(
            "deebot_client.messages.json.ngiot.GetBattery._handle_body_data_dict",
            return_value=HandlingResult.success(),
        ) as handle_battery,
        patch(
            "deebot_client.messages.json.ngiot.GetStats._handle_body_data_dict",
            return_value=HandlingResult.success(),
        ) as handle_stats,
        patch(
            "deebot_client.messages.json.ngiot.GetChildLock._handle_body_data_dict",
            return_value=HandlingResult.success(),
        ) as handle_child_lock,
        patch(
            "deebot_client.messages.json.ngiot.GetVolume._handle_body_data_dict",
            return_value=HandlingResult.success(),
        ) as handle_volume,
    ):
        result = OnNgiotStatusEvent.handle(event_bus, payload)

    assert result.state == HandlingState.SUCCESS
    handle_battery.assert_called_once_with(event_bus, payload["body"]["data"])
    handle_stats.assert_called_once_with(event_bus, payload["body"]["data"])
    handle_child_lock.assert_called_once_with(event_bus, payload["body"]["data"])
    handle_volume.assert_called_once_with(event_bus, payload["body"]["data"])
    event_bus.notify.assert_called_once_with(StateEvent(State.CLEANING))


def test_on_ngiot_status_event_falls_back_to_clean_info_when_state_unresolved() -> None:
    event_bus = Mock(spec_set=EventBus)
    event_bus.get_last_event.return_value = None
    payload = {
        "body": {
            "data": {
                "status": "unknown",
            }
        }
    }

    with patch(
        "deebot_client.messages.json.ngiot.GetCleanInfo._handle_body_data_dict",
        return_value=HandlingResult.success(),
    ) as handle_clean_info:
        result = OnNgiotStatusEvent.handle(event_bus, payload)

    assert result.state == HandlingState.SUCCESS
    handle_clean_info.assert_called_once_with(event_bus, payload["body"]["data"])
