from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

from deebot_client.capabilities import Capabilities
from deebot_client.const import DataType
from deebot_client.models import StaticDeviceInfo

if TYPE_CHECKING:
    from collections.abc import Mapping

    from deebot_client.command import Command
    from deebot_client.events.base import Event


def get_request_json(body: dict[str, Any]) -> dict[str, Any]:
    return {"id": "ALZf", "ret": "ok", "resp": get_message_json(body)}


def get_success_body(data: dict[str, Any] | None | list[Any] = None) -> dict[str, Any]:
    body = {
        "code": 0,
        "msg": "ok",
    }
    if data:
        body["data"] = data

    return body


def get_message_json(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "header": {
            "pri": 1,
            "tzm": 480,
            "ts": "1304623069888",
            "ver": "0.0.1",
            "fwVer": "1.8.2",
            "hwVer": "0.1.1",
        },
        "body": body,
    }


def mock_static_device_info(
    events: Mapping[type[Event], list[Command]] | None = None,
) -> StaticDeviceInfo[Capabilities]:
    """Mock static device info."""
    if events is None:
        events = {}

    mock = Mock(spec_set=Capabilities)

    def get_refresh_commands(event: type[Event]) -> list[Command]:
        return events.get(event, [])

    mock.get_refresh_commands.side_effect = get_refresh_commands

    return StaticDeviceInfo(DataType.JSON, mock)
