from collections.abc import Callable
import logging
from typing import Any
from unittest.mock import Mock

import pytest

from deebot_client.command import CommandWithMessageHandling
from deebot_client.commands.json import GetBattery
from deebot_client.commands.json.map import GetCachedMapInfo
from deebot_client.event_bus import EventBus
from deebot_client.events import AvailabilityEvent
from deebot_client.models import DeviceInfo

_ERROR_500 = {"ret": "fail", "errno": 500, "debug": "wait for response timed out"}
_ERROR_4200 = {
    "ret": "fail",
    "errno": 4200,
    "error": "endpoint offline",
    "debug": "jmq.clusterNode.FetchClientInfo rsp==null; no clientinfo in redis which means no ping was received from endpoint for a long time",
}


def _assert_false_and_not_called(available: bool, event_bus: Mock) -> None:
    assert available is False
    event_bus.assert_not_called()


def _assert_false_and_avalable_event_false(available: bool, event_bus: Mock) -> None:
    assert available is False
    event_bus.notify.assert_called_with(AvailabilityEvent(False))


@pytest.mark.parametrize(
    ("repsonse_json", "expected_log", "assert_func"),
    [
        (
            _ERROR_500,
            (
                logging.WARNING,
                'No response received for command "{}". This can happen if the device has network issues or does not support the command',
            ),
            _assert_false_and_not_called,
        ),
        (
            {"ret": "fail", "errno": 123, "debug": "other error"},
            (
                logging.WARNING,
                'Command "{}" was not successfully.',
            ),
            _assert_false_and_not_called,
        ),
        (
            _ERROR_4200,
            (
                logging.INFO,
                'Device is offline. Could not execute command "{}"',
            ),
            _assert_false_and_avalable_event_false,
        ),
    ],
)
@pytest.mark.parametrize(
    "command", [GetBattery(), GetBattery(True), GetCachedMapInfo()]
)
async def test_common_functionality(
    authenticator: Mock,
    device_info: DeviceInfo,
    command: CommandWithMessageHandling,
    repsonse_json: dict[str, Any],
    expected_log: tuple[int, str],
    assert_func: Callable[[bool, Mock], None],
    caplog: pytest.LogCaptureFixture,
) -> None:
    authenticator.post_authenticated.return_value = repsonse_json
    event_bus = Mock(spec_set=EventBus)

    available = await command.execute(authenticator, device_info, event_bus)

    if repsonse_json.get("errno") == 500 and command._is_available_check:
        assert (
            "deebot_client.command",
            logging.INFO,
            f'No response received for command "{command.name}" during availability-check.',
        ) in caplog.record_tuples

    elif expected_log:
        assert (
            "deebot_client.command",
            expected_log[0],
            expected_log[1].format(command.name),
        ) in caplog.record_tuples

    assert_func(available, event_bus)
