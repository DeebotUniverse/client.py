from __future__ import annotations

import asyncio
from collections.abc import Callable
import json
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

from deebot_client.command import Command, DeviceCommandResult
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.xml import GetBatteryInfo
from deebot_client.const import DataType
from deebot_client.device import Device
from deebot_client.events import AvailabilityEvent, StateEvent
from deebot_client.events.map import Position, PositionsEvent
from deebot_client.events.network import NetworkInfoEvent
from deebot_client.hardware import get_static_device_info
from deebot_client.messages.json import OnBattery
from deebot_client.messages.xml import BatteryInfo
from deebot_client.models import DeviceInfo, StaticDeviceInfo
from deebot_client.mqtt_client import MqttClient, SubscriberInfo
from deebot_client.rs.map import PositionType
from tests.helpers import mock_static_device_info
from tests.helpers.tasks import block_till_done

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.event_bus import EventBus
    from deebot_client.message import Message
    from deebot_client.models import ApiDeviceInfo


def json_battery_message_payload(expected_version: str | None = "1.8.2") -> str:
    header = {
        "pri": 1,
        "tzm": 480,
        "ts": "1304637391896",
        "ver": "0.0.1",
        "hwVer": "0.1.1",
    }
    if expected_version:
        header.update({"fwVer": expected_version})
    data = {
        "header": header,
        "body": {"data": {"value": 100, "isLow": 0}},
    }
    return json.dumps(data)


def xml_battery_message_payload() -> str:
    return '<ctl ret="ok"><battery power="100" /></ctl>'


@pytest.mark.parametrize(
    ("data_type", "get_battery_command", "battery_message", "battery_message_payload"),
    [
        (DataType.JSON, GetBattery, OnBattery, json_battery_message_payload()),
        (DataType.XML, GetBatteryInfo, BatteryInfo, xml_battery_message_payload()),
    ],
    ids=["json_bot", "xml_bot"],
)
@patch("deebot_client.device._AVAILABLE_CHECK_INTERVAL", 2)  # reduce interval
async def test_available_check_and_teardown(
    data_type: DataType,
    get_battery_command: Command,
    battery_message: Message,
    battery_message_payload: str,
    authenticator: Authenticator,
    api_device_info: ApiDeviceInfo,
) -> None:
    """Test the available check including if the status Event is fired correctly."""
    received_statuses: asyncio.Queue[AvailabilityEvent] = asyncio.Queue()

    async def on_status(event: AvailabilityEvent) -> None:
        received_statuses.put_nowait(event)

    async def assert_received_status(*, expected: bool) -> None:
        await asyncio.sleep(0.1)
        assert received_statuses.get_nowait().available is expected

    # prepare mocks
    battery_mock = Mock(spec_set=get_battery_command)

    device_info = DeviceInfo(
        api_device_info,
        mock_static_device_info({AvailabilityEvent: [battery_mock]}, data_type),
    )
    execute_mock = battery_mock.execute

    # prepare bot and mock mqtt
    bot = Device(device_info, authenticator)
    mqtt_client = Mock(spec=MqttClient)
    unsubscribe_mock = Mock(spec=Callable[[], None])
    mqtt_client.subscribe.return_value = unsubscribe_mock
    await bot.initialize(mqtt_client)

    # deactivate refresh event subscribe refresh calls
    bot.events._get_refresh_commands = lambda _: []

    bot.events.subscribe(AvailabilityEvent, on_status)

    # verify mqtt was subscribed and available task was started
    mqtt_client.subscribe.assert_called_once()
    sub_info: SubscriberInfo = mqtt_client.subscribe.call_args.args[0]
    assert bot._available_task is not None
    assert not bot._available_task.done()
    # As task was started now, no check should be performed
    execute_mock.assert_not_called()

    # Simulate bot not reached by returning False
    execute_mock.return_value = DeviceCommandResult(device_reached=False)

    # Wait longer than the interval to be sure task will be executed
    await asyncio.sleep(2.1)
    # Verify command call for available check
    execute_mock.assert_awaited_once()
    await assert_received_status(expected=False)

    # Simulate bot reached by returning True
    execute_mock.return_value = DeviceCommandResult(device_reached=True)

    await asyncio.sleep(2)
    execute_mock.await_count = 2
    await assert_received_status(expected=True)

    # reset mock for easier handling
    battery_mock.reset_mock()

    # Simulate message over mqtt and therefore available is not needed
    await asyncio.sleep(0.8)

    sub_info.callback(battery_message.NAME, battery_message_payload)
    await asyncio.sleep(1)

    # As the last message is not more than (interval-1) old, we skip the available check
    execute_mock.assert_not_called()
    assert received_statuses.empty()

    # teardown bot and verify that bot was unsubscribed from mqtt and available task was canceled.
    await bot.teardown()
    await asyncio.sleep(0.1)

    unsubscribe_mock.assert_called()
    assert bot._available_task.done()
    await bot.teardown()


async def test_mac_address(
    authenticator: Authenticator, device_info: DeviceInfo
) -> None:
    """Test that the mac address is change on NetworkInfoEvent."""
    device = Device(device_info, authenticator)
    # deactivate refresh event subscribe refresh calls
    device.events._get_refresh_commands = lambda _: []

    assert device.mac is None

    mac = "AA:BB:CC:DD:EE:FF"

    device.events.notify(
        NetworkInfoEvent(ip="192.168.1.100", ssid="WLAN", rssi=-61, mac=mac)
    )

    await block_till_done(device.events._tasks)

    assert device.mac == mac
    await device.teardown()


def static_device_info_no_map() -> StaticDeviceInfo:
    """Return a StaticDeviceInfo without map capability."""
    info = asyncio.run(get_static_device_info("2ap5uq"))
    assert info is not None
    assert info.capabilities.map is None
    return info


@pytest.mark.parametrize(
    "static_device_info",
    [
        static_device_info_no_map(),
    ],
)
async def test_behaviour_with_no_map_capability(
    authenticator: Authenticator, device_info: DeviceInfo
) -> None:
    device = Device(device_info, authenticator)

    assert device.map is None

    await device.teardown()


@pytest.mark.parametrize(
    (
        "data_type",
        "get_battery_command",
        "battery_message",
        "battery_message_payload",
        "expected_version",
    ),
    [
        (
            DataType.JSON,
            GetBattery,
            OnBattery,
            json_battery_message_payload("1.8.2"),
            "1.8.2",
        ),
        (
            DataType.JSON,
            GetBattery,
            OnBattery,
            json_battery_message_payload(None),
            None,
        ),
        (DataType.JSON, GetBattery, OnBattery, "{corrupted}", None),
        (DataType.JSON, GetBattery, OnBattery, '["not an object"]', None),
        (
            DataType.XML,
            GetBatteryInfo,
            BatteryInfo,
            xml_battery_message_payload(),
            None,
        ),
    ],
    ids=[
        "json_bot",
        "json_bot_no_version",
        "json_bot_corrupted_json",
        "json_bot_not_a_dict_json",
        "xml_bot",
    ],
)
@patch("deebot_client.device._AVAILABLE_CHECK_INTERVAL", 2)  # reduce interval
async def test_device_handle_message_behaviour(
    data_type: DataType,
    get_battery_command: Command,
    battery_message: Message,
    battery_message_payload: str,
    expected_version: str | None,
    authenticator: Authenticator,
    api_device_info: ApiDeviceInfo,
) -> None:
    """Test the available check including if the status Event is fired correctly."""
    received_statuses: asyncio.Queue[AvailabilityEvent] = asyncio.Queue()

    async def on_status(event: AvailabilityEvent) -> None:
        received_statuses.put_nowait(event)

    # prepare mocks
    battery_mock = Mock(spec_set=get_battery_command)

    device_info = DeviceInfo(
        api_device_info,
        mock_static_device_info({AvailabilityEvent: [battery_mock]}, data_type),
    )

    # prepare bot and mock mqtt
    bot = Device(device_info, authenticator)
    mqtt_client = Mock(spec=MqttClient)
    unsubscribe_mock = Mock(spec=Callable[[], None])
    mqtt_client.subscribe.return_value = unsubscribe_mock
    await bot.initialize(mqtt_client)

    # deactivate refresh event subscribe refresh calls
    bot.events._get_refresh_commands = lambda _: []

    bot.events.subscribe(AvailabilityEvent, on_status)

    # verify mqtt was subscribed and available task was started
    mqtt_client.subscribe.assert_called_once()
    sub_info: SubscriberInfo = mqtt_client.subscribe.call_args.args[0]
    sub_info.callback(battery_message.NAME, battery_message_payload)
    await asyncio.sleep(1)

    assert bot.fw_version == expected_version

    # teardown bot
    await bot.teardown()


@pytest.mark.parametrize(
    ("pos_event", "expected_call"),
    [
        (PositionsEvent([]), False),
        (PositionsEvent([Position(PositionType.CHARGER, 0, 0, 0)]), False),
        (PositionsEvent([Position(PositionType.DEEBOT, 0, 0, 0)]), False),
        (
            PositionsEvent(
                [
                    Position(PositionType.DEEBOT, 0, 0, 0),
                    Position(PositionType.CHARGER, 0, 0, 0),
                ]
            ),
            True,
        ),
        (
            PositionsEvent(
                [
                    Position(PositionType.CHARGER, 0, 0, 0),
                    Position(PositionType.DEEBOT, 0, 0, 0),
                ]
            ),
            True,
        ),
        (
            PositionsEvent(
                [
                    Position(PositionType.CHARGER, 1, 0, 0),
                    Position(PositionType.DEEBOT, 0, 0, 0),
                ]
            ),
            False,
        ),
        (
            PositionsEvent(
                [
                    Position(PositionType.DEEBOT, 0, 0, 0),
                    Position(PositionType.CHARGER, 1, 0, 0),
                ]
            ),
            False,
        ),
        (
            PositionsEvent(
                [
                    Position(PositionType.DEEBOT, 0, 0, 0),
                    Position(PositionType.CHARGER, 1, 0, 0),
                    Position(PositionType.CHARGER, 0, 0, 0),
                ]
            ),
            True,
        ),
    ],
)
async def test_onPos_device_handling(
    authenticator: Authenticator,
    device_info: DeviceInfo,
    event_bus_mock: Mock,
    event_bus: EventBus,
    pos_event: PositionsEvent,
    expected_call: bool,
) -> None:
    """Test the available check including if the status Event is fired correctly."""
    with patch("deebot_client.device.EventBus", return_value=event_bus_mock):
        bot = Device(device_info, authenticator)
        mqtt_client = Mock(spec=MqttClient)
        unsubscribe_mock = Mock(spec=Callable[[], None])
        mqtt_client.subscribe.return_value = unsubscribe_mock
        await bot.initialize(mqtt_client)

    bot.events.notify(pos_event)
    await block_till_done(event_bus._tasks)

    if expected_call:
        event_bus_mock.request_refresh.assert_called_once_with(StateEvent)
    else:
        event_bus_mock.request_refresh.assert_not_called()

    # teardown bot
    await bot.teardown()
