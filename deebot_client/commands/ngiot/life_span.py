"""Life span commands."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from deebot_client.events import LifeSpan, LifeSpanEvent
from deebot_client.exceptions import ApiError
from deebot_client.message import HandlingResult

from .common import RobotDetailGetCommand, RobotDetailSetCommand

_CONSUMABLE_TYPES: dict[str, LifeSpan] = {
    'rollBrush': LifeSpan.BRUSH,
    'filter': LifeSpan.FILTER,
    'sideBrush': LifeSpan.SIDE_BRUSH,
    'unitCare': LifeSpan.UNIT_CARE,
}


class GetLifeSpan(RobotDetailGetCommand):
    """Get consumable life-span data."""

    NAME = 'getLifeSpan'
    FIELDS = ('consumables',)

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus,
        data: dict[str, Any],
    ) -> HandlingResult:
        for item in data.get('consumables', []) or []:
            if not isinstance(item, Mapping):
                continue
            consumable_type = _CONSUMABLE_TYPES.get(str(item.get('type')))
            if consumable_type is None:
                continue
            left = int(item.get('left', 0) or 0)
            total = int(item.get('total', 0) or 0)
            percent = 0.0 if total <= 0 else (left / total) * 100
            event_bus.notify(LifeSpanEvent(consumable_type, percent, left))
        return HandlingResult.success()


class ResetLifeSpan(RobotDetailSetCommand):
    """Reset a consumable counter.

    Left intentionally unimplemented until the reset payload is captured.
    """

    NAME = 'resetLifeSpan'

    def __init__(self, life_span: LifeSpan) -> None:
        super().__init__({'lifeSpan': life_span.name})
        self._life_span = life_span

    def _get_body_data(self) -> dict[str, Any]:
        raise ApiError('Life-span reset payload has not been captured for NGIOT yet')
