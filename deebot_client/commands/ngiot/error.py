"""Error commands."""

from __future__ import annotations

from typing import Any

from deebot_client.events import ErrorEvent
from deebot_client.message import HandlingResult

from .common import RobotDetailGetCommand


class GetError(RobotDetailGetCommand):
    """Get current robot error."""

    NAME = 'getError'
    FIELDS = ('error',)

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus,
        data: dict[str, Any],
    ) -> HandlingResult:
        event_bus.notify(ErrorEvent(_extract_first_int(data.get('error'))))
        return HandlingResult.success()


def _extract_first_int(value: Any) -> int:
    if isinstance(value, list) and value:
        value = value[0]
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
