"""NGIOT fan speed commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import FanSpeedEvent, FanSpeedLevel
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.ngiot_client import NgiotRequest
from deebot_client.util import get_enum

from .common import APN_FAN_MODE, NgiotExecuteCommand, RobotDetailGetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo
    from deebot_client.ngiot_client import NgiotClient

_WIRE_TO_LEVEL: dict[str, FanSpeedLevel] = {
    "quiet": FanSpeedLevel.QUIET,
    "auto": FanSpeedLevel.NORMAL,
    "strong": FanSpeedLevel.MAX,
    "max": FanSpeedLevel.MAX_PLUS,
}

_LEVEL_TO_WIRE: dict[FanSpeedLevel, str] = {
    FanSpeedLevel.QUIET: "quiet",
    FanSpeedLevel.NORMAL: "auto",
    FanSpeedLevel.MAX: "strong",
    FanSpeedLevel.MAX_PLUS: "max",
}


class GetFanSpeed(RobotDetailGetCommand):
    """Get current fan speed/mode from robot detail status."""

    NAME = "getSpeed"
    FIELDS = ("fanMode",)

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus: EventBus,
        data: dict[str, Any],
    ) -> HandlingResult:
        fan_mode = data.get("fanMode")
        if fan_mode is None:
            return HandlingResult.analyse()
        fan_speed = _WIRE_TO_LEVEL.get(str(fan_mode).lower())
        if fan_speed is None:
            return HandlingResult.analyse()
        event_bus.notify(FanSpeedEvent(fan_speed))
        return HandlingResult.success()


class SetFanSpeed(NgiotExecuteCommand):
    """Set fan speed/mode for NGIOT devices."""

    NAME = "setSpeed"
    get_command = GetFanSpeed

    def __init__(self, speed: FanSpeedLevel | str) -> None:
        super().__init__({})
        if isinstance(speed, str):
            speed = get_enum(FanSpeedLevel, speed)
        self._speed = speed

    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        try:
            fan_mode = _LEVEL_TO_WIRE[self._speed]
        except KeyError as ex:
            msg = f"Fan speed {self._speed!s} is not supported by this NGIOT ruleset"
            raise ValueError(msg) from ex
        return await client.request(
            device_info,
            NgiotRequest(apn=APN_FAN_MODE, body_data={"fanMode": fan_mode}),
        )

    def _handle_response(
        self,
        event_bus: EventBus,
        response: dict[str, Any],
    ) -> HandlingResult:
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.notify(FanSpeedEvent(self._speed))
        return result
