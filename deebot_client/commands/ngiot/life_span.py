"""Life span commands."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from deebot_client.events import LifeSpan, LifeSpanEvent
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.ngiot_client import NgiotRequest
from deebot_client.util import get_enum

from .common import APN_RESET_CONSUMABLE, NgiotExecuteCommand, RobotDetailGetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo
    from deebot_client.ngiot_client import NgiotClient

_CONSUMABLE_TYPES: dict[str, LifeSpan] = {
    "rollBrush": LifeSpan.BRUSH,
    "filter": LifeSpan.FILTER,
    "sideBrush": LifeSpan.SIDE_BRUSH,
    "unitCare": LifeSpan.UNIT_CARE,
}

_RESET_CONSUMABLE_TYPES: dict[LifeSpan, str] = {
    LifeSpan.BRUSH: "rollBrush",
    LifeSpan.FILTER: "filter",
    LifeSpan.SIDE_BRUSH: "sideBrush",
    LifeSpan.UNIT_CARE: "unitCare",
}


class GetLifeSpan(RobotDetailGetCommand):
    """Get consumable life-span data."""

    NAME = "getLifeSpan"
    FIELDS = ("consumables",)

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus: EventBus,
        data: dict[str, Any],
    ) -> HandlingResult:
        for item in data.get("consumables", []) or []:
            if not isinstance(item, Mapping):
                continue
            consumable_type = _CONSUMABLE_TYPES.get(str(item.get("type")))
            if consumable_type is None:
                continue
            left = int(item.get("left", 0) or 0)
            total = int(item.get("total", 0) or 0)
            percent = 0.0 if total <= 0 else (left / total) * 100
            event_bus.notify(LifeSpanEvent(consumable_type, percent, left))
        return HandlingResult.success()


class ResetLifeSpan(NgiotExecuteCommand):
    """Reset a consumable counter via the NGIOT reset-consumable surface."""

    NAME = "resetLifeSpan"
    get_command = GetLifeSpan

    def __init__(self, life_span: LifeSpan | str) -> None:
        super().__init__({})
        if isinstance(life_span, str):
            life_span = get_enum(LifeSpan, life_span)
        self._life_span = life_span

    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        try:
            reset_consumable = _RESET_CONSUMABLE_TYPES[self._life_span]
        except KeyError as ex:
            msg = (
                "Life-span reset is not supported for NGIOT consumable "
                f"{self._life_span!s}"
            )
            raise ValueError(msg) from ex
        return await client.request(
            device_info,
            NgiotRequest(
                apn=APN_RESET_CONSUMABLE,
                body_data={"resetConsumable": reset_consumable},
            ),
        )

    def _handle_response(
        self,
        event_bus: EventBus,
        response: dict[str, Any],
    ) -> HandlingResult:
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.request_refresh(LifeSpanEvent)
        return result
