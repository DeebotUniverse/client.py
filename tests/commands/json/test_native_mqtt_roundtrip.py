"""Native map MQTT registry and request/reply round-trip tests (no broker)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

import orjson

from deebot_client.commands import COMMANDS_WITH_MQTT_P2P_HANDLING
from deebot_client.commands.json.native_map import GetNativeMapData, NativeMapSwitch
from deebot_client.commands.json.native_map_edit import NativeMapOverlay
from deebot_client.commands.json.native_room_edit import (
    NativeMergeRooms,
    NativeRenameRoom,
    NativeSplitRoom,
)
from deebot_client.const import DataType
from deebot_client.event_bus import EventBus
from deebot_client.events import CachedMapInfoEvent, MapSetType
from deebot_client.hardware.cqyi87 import get_device_info
from deebot_client.map import Map
from deebot_client.mqtt_client import MqttClient, MqttConfiguration, SubscriberInfo
from tests.common import block_till_done

if TYPE_CHECKING:
    from deebot_client.models import DeviceInfo


def _subscribed_client(device_info: DeviceInfo, events: EventBus) -> MqttClient:
    client = MqttClient(
        MqttConfiguration(
            hostname="localhost", port=1883, ssl_context=None, device_id="tester"
        ),
        Mock(),
    )
    client._subscriptions[device_info.api["did"]] = SubscriberInfo(
        device_info, events, Mock()
    )
    return client


def _request_topic(command: str, device_info: DeviceInfo, request_id: str) -> str:
    api = device_info.api
    return (
        f"iot/p2p/{command}/test/test/test/"
        f"{api['did']}/{api['class']}/{api['resource']}/q/{request_id}/j"
    )


def _response_topic(command: str, device_info: DeviceInfo, request_id: str) -> str:
    api = device_info.api
    return (
        f"iot/p2p/{command}/{api['did']}/{api['class']}/{api['resource']}/"
        f"test/test/test/p/{request_id}/j"
    )


def test_native_commands_registered_for_p2p() -> None:
    """Given command registry, when looked up, then native edits route."""
    registry = COMMANDS_WITH_MQTT_P2P_HANDLING[DataType.JSON]
    assert registry["30004"] is NativeMapSwitch
    assert registry["50001"] is NativeMapOverlay
    assert registry["50005"] is NativeSplitRoom
    assert registry["50007"] is NativeMergeRooms
    assert registry["50009"] is NativeRenameRoom


async def _refresh_observing_bus(execute_mock: AsyncMock) -> EventBus:
    _caps = get_device_info().capabilities
    bus = EventBus(execute_mock, _caps)
    assert _caps.map is not None
    Map(execute_mock, bus, _caps.map)

    async def _on_catalog(_: CachedMapInfoEvent) -> None:
        pass

    bus.subscribe(CachedMapInfoEvent, _on_catalog)
    await block_till_done(bus)
    execute_mock.reset_mock()
    return bus


async def test_switch_request_reply_roundtrip(device_info: DeviceInfo) -> None:
    """Given 30004 switch capture shape, when q then p, then refresh."""
    execute_mock = AsyncMock()
    bus = await _refresh_observing_bus(execute_mock)
    client = _subscribed_client(device_info, bus)
    request_id = "JcXrC6"
    client._handle_p2p(
        _request_topic("30004", device_info, request_id).split("/"),
        orjson.dumps(
            {"body": {"data": {"mapId": "2", "request": "mapSwitch"}}},
        ),
    )
    assert client._received_p2p_commands[request_id] == NativeMapSwitch("2")
    client._handle_p2p(
        _response_topic("30004", device_info, request_id).split("/"),
        orjson.dumps({"body": {"code": 0, "data": {"mapId": "2"}, "msg": "ok"}}),
    )
    await block_till_done(bus)
    assert execute_mock.call_count == 4
    fetched = [call.args[0] for call in execute_mock.call_args_list]
    assert all(isinstance(command, GetNativeMapData) for command in fetched)
    assert sum(command.fields == ["mapInfos"] for command in fetched) == 1
    assert sum(command.map_id == "2" for command in fetched) == 3


async def test_switch_failed_ack_queues_nothing(device_info: DeviceInfo) -> None:
    """Given 30004 failure reply, when p arrives, then no refresh."""
    execute_mock = AsyncMock()
    bus = await _refresh_observing_bus(execute_mock)
    client = _subscribed_client(device_info, bus)
    request_id = "JcXrC6"
    client._handle_p2p(
        _request_topic("30004", device_info, request_id).split("/"),
        orjson.dumps(
            {"body": {"data": {"mapId": "2", "request": "mapSwitch"}}},
        ),
    )
    client._handle_p2p(
        _response_topic("30004", device_info, request_id).split("/"),
        orjson.dumps({"body": {"code": 500, "msg": "fail"}}),
    )
    await block_till_done(bus)
    execute_mock.assert_not_called()


async def test_overlay_request_reply_roundtrip(device_info: DeviceInfo) -> None:
    """Given 50001 add-wall shape, when q then p ok, then refresh."""
    execute_mock = AsyncMock()
    bus = await _refresh_observing_bus(execute_mock)
    client = _subscribed_client(device_info, bus)
    request_id = "ovl1"
    client._handle_p2p(
        _request_topic("50001", device_info, request_id).split("/"),
        orjson.dumps(
            {
                "body": {
                    "data": {
                        "action": "add",
                        "mode": 1,
                        "type": 1,
                        "mapId": "m1",
                        "point": "1,2,3,4",
                    }
                }
            },
        ),
    )
    assert client._received_p2p_commands[request_id] == NativeMapOverlay(
        "add", MapSetType.VIRTUAL_WALLS, "m1", [1, 2, 3, 4]
    )
    client._handle_p2p(
        _response_topic("50001", device_info, request_id).split("/"),
        orjson.dumps({"body": {"code": 0, "msg": "ok"}}),
    )
    await block_till_done(bus)
    assert execute_mock.call_count == 3
    for call in execute_mock.call_args_list:
        command = call.args[0]
        assert isinstance(command, GetNativeMapData)
        assert command.map_id == "m1"
