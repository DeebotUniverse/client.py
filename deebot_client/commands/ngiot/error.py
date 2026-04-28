"""Error commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import ErrorEvent
from deebot_client.message import HandlingResult

from .common import RobotDetailGetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetError(RobotDetailGetCommand):
    """Get current robot error."""

    NAME = "getError"
    FIELDS = ("error",)

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus: EventBus,
        data: dict[str, Any],
    ) -> HandlingResult:
        code = _extract_first_int(data.get("error"))

        if code == 0:
            return HandlingResult.success()

        event_bus.notify(ErrorEvent(code, f"NGIOT error {code}"))
        return HandlingResult.success()


def _extract_first_int(value: Any) -> int:
    if isinstance(value, list) and value:
        value = value[0]
    try:
        return int(value)
    except TypeError, ValueError:
        return 0
