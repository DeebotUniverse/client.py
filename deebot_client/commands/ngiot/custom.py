"""Custom commands."""

from __future__ import annotations

from typing import Any

from deebot_client.events import CustomCommandEvent
from deebot_client.message import HandlingResult, HandlingState

from .common import RobotDetailSetCommand


class CustomCommand(RobotDetailSetCommand):
    """Send an arbitrary key/value payload to APN 10001."""

    NAME = 'customCommand'

    def __init__(self, name: str, value: Any) -> None:
        super().__init__({name: value})
        self._name = name
        self._value = value

    def _get_body_data(self) -> dict[str, Any]:
        return dict(self._args)

    def _handle_response(self, event_bus, response: dict[str, Any]) -> HandlingResult:
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            body = response.get('resp', {}).get('body', {})
            event_bus.notify(CustomCommandEvent(name=self._name, response=body))
        return result
