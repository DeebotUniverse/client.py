from collections.abc import Mapping
from typing import Any
from unittest.mock import Mock

from deebot_client.capabilities import Capabilities
from deebot_client.command import Command
from deebot_client.events.base import Event
from deebot_client.util import DisplayNameIntEnum


def verify_DisplayNameEnum_unique(enum: type[DisplayNameIntEnum]) -> None:
    assert issubclass(enum, DisplayNameIntEnum)
    names: set[str] = set()
    values: set[int] = set()
    for member in enum:
        assert member.value not in values
        values.add(member.value)

        name = member.name.lower()
        assert name not in names
        names.add(name)

        display_name = member.display_name.lower()
        if display_name != name:
            assert display_name not in names
            names.add(display_name)


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


def get_mocked_capabilities(
    events: Mapping[type[Event], list[Command]] | None = None
) -> Capabilities:
    """Get test capabilities."""
    if events is None:
        events = {}

    mock = Mock(spec_set=Capabilities)

    def get_refresh_commands(event: type[Event]) -> list[Command]:
        return events.get(event, [])

    mock.get_refresh_commands.side_effect = get_refresh_commands

    return mock
