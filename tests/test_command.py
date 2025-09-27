from __future__ import annotations

import json
import logging
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from aiohttp import ClientTimeout
import pytest

from deebot_client.command import Command, InitParam
from deebot_client.commands.json.common import JsonCommandMqttP2P
from deebot_client.exceptions import ApiTimeoutError, DeebotError
from deebot_client.message import HandlingResult

if TYPE_CHECKING:
    from unittest.mock import Mock

    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo


class _TestCommand(JsonCommandMqttP2P):
    NAME = "TestCommand"
    _mqtt_params = MappingProxyType({"field": InitParam(int), "remove": None})

    def __init__(self, field: int) -> None:
        pass

    def _handle_mqtt_p2p(
        self, event_bus: EventBus, response: dict[str, Any] | str
    ) -> None:
        pass

    def _get_payload(self) -> dict[str, Any] | list[Any]:
        return {}

    def _handle_response(
        self,
        _: EventBus,
        response: dict[str, Any],  # noqa: ARG002
    ) -> HandlingResult:
        return HandlingResult.analyse()


def test_CommandMqttP2P_no_mqtt_params() -> None:
    class TestCommandNoParams(JsonCommandMqttP2P):
        NAME = "TestCommand"

    with pytest.raises(DeebotError, match=r"_mqtt_params not set"):
        TestCommandNoParams.create_from_mqtt(b'{"body": {"data": {}}}')


def test_Command_no_NAME() -> None:
    with pytest.raises(
        ValueError, match="Class TestCommand must have a NAME attribute"
    ):

        class TestCommand(Command):
            pass


def test_Command_no_DATA_TYPE() -> None:
    with pytest.raises(
        ValueError, match="Class TestCommand must have a DATA_TYPE attribute"
    ):

        class TestCommand(Command):
            NAME = "TestCommand"


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"field": "a"}, r"""Could not convert "a" of field into <class 'int'>"""),
        ({"something": "a"}, r'"field" is missing in {\'something\': \'a\'}'),
    ],
)
def test_CommandMqttP2P_create_from_mqtt_error(
    data: dict[str, str], expected: str
) -> None:
    with pytest.raises(DeebotError, match=expected):
        _TestCommand.create_from_mqtt(json.dumps({"body": {"data": data}}))


def test_CommandMqttP2P_create_from_mqtt_additional_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    _TestCommand.create_from_mqtt(
        b'{"body":{"data":{"field": 0, "remove": "bla", "additional": 1}}}'
    )
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
    authenticator.post_authenticated.side_effect = ApiTimeoutError(
        "test", ClientTimeout(60)
    )
    result = await command.execute(authenticator, api_device_info, event_bus_mock)
    assert not result.device_reached
    assert (
        "deebot_client.command",
        logging.WARNING,
        "Could not execute command TestCommand for get_class: Timeout reached",
    ) in caplog.record_tuples
