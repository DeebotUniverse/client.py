"""Child lock commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import ChildLockEvent
from deebot_client.message import HandlingResult, HandlingState

from .common import (
    ExecuteCommand,
    GetEnableCommand,
    NgiotJsonCommand,
    SetEnableCommand,
)

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetChildLock(GetEnableCommand):
    """Get child lock command."""

    NAME = "getChildLock"
    EVENT_TYPE = ChildLockEvent
    _field_name = "on"


class SetChildLock(SetEnableCommand):
    """Set child lock command."""

    NAME = "setChildLock"
    get_command = GetChildLock
    _field_name = "on"


class NgiotGetChildLock(NgiotJsonCommand, GetChildLock):
    """Get child lock state through NGIOT."""

    NAME = "ngiotGetChildLock"
    APN = "10001"
    _field_name = "childLock"

    def __init__(self) -> None:
        super().__init__({"fields": ["childLock"]})

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        if not isinstance(data.get(cls._field_name), bool):
            return HandlingResult.analyse()
        return super()._handle_body_data_dict(event_bus, data)


class NgiotSetChildLock(NgiotJsonCommand, ExecuteCommand):
    """Set child lock through NGIOT and request the updated state."""

    NAME = "ngiotSetChildLock"
    APN = "50038"

    def __init__(self, enable: bool) -> None:
        if not isinstance(enable, bool):
            raise TypeError("Child lock must be a boolean")
        super().__init__({"childLock": enable})

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        result = super()._handle_body(event_bus, body)
        if result.state == HandlingState.SUCCESS:
            return HandlingResult(
                result.state, requested_commands=[NgiotGetChildLock()]
            )
        return result
