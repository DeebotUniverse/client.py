from collections.abc import Callable
from typing import Any
from unittest.mock import Mock

import pytest
from testfixtures import LogCapture

from deebot_client.commands import GetBattery
from deebot_client.commands.common import CommandWithMessageHandling
from deebot_client.commands.map import GetCachedMapInfo
from deebot_client.events import AvailabilityEvent
from deebot_client.events.event_bus import EventBus
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
    "repsonse_json, expected_log, assert_func",
    [
        (
            _ERROR_500,
            (
                "WARNING",
                'No response received for command "{}". This can happen if the vacuum has network issues or does not support the command',
            ),
            _assert_false_and_not_called,
        ),
        (
            {"ret": "fail", "errno": 123, "debug": "other error"},
            (
                "WARNING",
                'Command "{}" was not successfully.',
            ),
            _assert_false_and_not_called,
        ),
        (
            _ERROR_4200,
            (
                "INFO",
                'Vacuum is offline. Could not execute command "{}"',
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
    expected_log: tuple[str, str],
    assert_func: Callable[[bool, Mock], None],
) -> None:
    authenticator.post_authenticated.return_value = repsonse_json
    event_bus = Mock(spec_set=EventBus)

    with LogCapture() as log:
        available = await command.execute(authenticator, device_info, event_bus)

        if repsonse_json.get("errno") == 500 and command._is_available_check:
            log.check_present(
                (
                    "deebot_client.commands.common",
                    "INFO",
                    f'No response received for command "{command.name}" during availability-check.',
                )
            )
        elif expected_log:
            log.check_present(
                (
                    "deebot_client.commands.common",
                    expected_log[0],
                    expected_log[1].format(command.name),
                )
            )

        assert_func(available, event_bus)
