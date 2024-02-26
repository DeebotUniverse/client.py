from __future__ import annotations

import logging
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.command import CommandMqttP2P, CommandResult, InitParam
from deebot_client.const import DataType
from deebot_client.exceptions import ApiTimeoutError, DeebotError

if TYPE_CHECKING:
    from unittest.mock import Mock

    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo


class _TestCommand(CommandMqttP2P):
    name = "TestCommand"
    data_type = DataType.JSON
    _mqtt_params = MappingProxyType({"field": InitParam(int), "remove": None})

    def __init__(self, field: int) -> None:
        pass

    def handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        pass

    def _get_payload(self) -> dict[str, Any] | list[Any] | str:
        return {}

    def _handle_response(
        self,
        _: EventBus,
        response: dict[str, Any],  # noqa: ARG002
    ) -> CommandResult:
        return CommandResult.analyse()


def test_CommandMqttP2P_no_mqtt_params() -> None:
    class TestCommandNoParams(CommandMqttP2P):
        pass

    with pytest.raises(DeebotError, match=r"_mqtt_params not set"):
        TestCommandNoParams.create_from_mqtt({})


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"field": "a"}, r"""Could not convert "a" of field into <class 'int'>"""),
        ({"something": "a"}, r'"field" is missing in {\'something\': \'a\'}'),
    ],
)
def test_CommandMqttP2P_create_from_mqtt_error(
    data: dict[str, Any], expected: str
) -> None:
    with pytest.raises(DeebotError, match=expected):
        _TestCommand.create_from_mqtt(data)


def test_CommandMqttP2P_create_from_mqtt_additional_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    _TestCommand.create_from_mqtt({"field": 0, "remove": "bla", "additional": 1})
    assert (
        "deebot_client.command",
        logging.DEBUG,
        "Following data will be ignored: {'additional': 1}",
    ) in caplog.record_tuples


async def test_execute_api_timeout_error(
    caplog: pytest.LogCaptureFixture,
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
) -> None:
    """Test that on api timeout the stack trace is not logged."""
    command = _TestCommand(1)
    authenticator.post_authenticated.side_effect = ApiTimeoutError("test", 60)
    assert not await command.execute(authenticator, api_device_info, event_bus_mock)
    assert (
        "deebot_client.command",
        logging.WARNING,
        "Could not execute command TestCommand: Timeout reached",
    ) in caplog.record_tuples
