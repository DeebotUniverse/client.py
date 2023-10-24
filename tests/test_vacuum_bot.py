import asyncio
from collections.abc import Callable
import json
from unittest.mock import Mock, patch

from deebot_client.authentication import Authenticator
from deebot_client.commands.json.battery import GetBattery
from deebot_client.events import AvailabilityEvent
from deebot_client.models import DeviceInfo
from deebot_client.mqtt_client import MqttClient, SubscriberInfo
from deebot_client.vacuum_bot import VacuumBot
from tests.helpers import mock_static_device_info


@patch("deebot_client.vacuum_bot._AVAILABLE_CHECK_INTERVAL", 2)  # reduce interval
async def test_available_check_and_teardown(
    authenticator: Authenticator, device_info: DeviceInfo
) -> None:
    """Test the available check including if the status Event is fired correctly."""
    received_statuses: asyncio.Queue[AvailabilityEvent] = asyncio.Queue()

    async def on_status(event: AvailabilityEvent) -> None:
        received_statuses.put_nowait(event)

    async def assert_received_status(expected: bool) -> None:
        await asyncio.sleep(0.1)
        assert received_statuses.get_nowait().available is expected

    # prepare mocks
    battery_mock = Mock(spec_set=GetBattery)
    device_info._static_device_info = mock_static_device_info(
        {AvailabilityEvent: [battery_mock]}
    )
    execute_mock = battery_mock.execute

    # prepare bot and mock mqtt
    bot = VacuumBot(device_info, authenticator)
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
    execute_mock.return_value = False

    # Wait longer than the interval to be sure task will be executed
    await asyncio.sleep(2.1)
    # Verify command call for available check
    execute_mock.assert_awaited_once()
    await assert_received_status(False)

    # Simulate bot reached by returning True
    execute_mock.return_value = True

    await asyncio.sleep(2)
    execute_mock.await_count = 2
    await assert_received_status(True)

    # reset mock for easier handling
    battery_mock.reset_mock()

    # Simulate message over mqtt and therefore available is not needed
    await asyncio.sleep(0.8)
    data = {
        "header": {
            "pri": 1,
            "tzm": 480,
            "ts": "1304637391896",
            "ver": "0.0.1",
            "fwVer": "1.8.2",
            "hwVer": "0.1.1",
        },
        "body": {"data": {"value": 100, "isLow": 0}},
    }

    sub_info.callback("onBattery", json.dumps(data))
    await asyncio.sleep(1)

    # As the last message is not more than (interval-1) old, we skip the available check
    execute_mock.assert_not_called()
    assert received_statuses.empty()

    # teardown bot and verify that bot was unsubscribed from mqtt and available task was canceled.
    await bot.teardown()
    await asyncio.sleep(0.1)

    unsubscribe_mock.assert_called()
    assert bot._available_task.done()
