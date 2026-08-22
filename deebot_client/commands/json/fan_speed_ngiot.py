"""Fan speed command via ngiot endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import aiohttp

from deebot_client.events import FanSpeedEvent
from deebot_client.events.fan_speed import FanSpeedLevel
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.util import get_enum

from .common import JsonCommandWithMessageHandling, get_sst, ngiot_post

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo

_LOGGER = get_logger(__name__)

_FAN_LEVEL_TO_MODE: dict[FanSpeedLevel, str] = {
    FanSpeedLevel.QUIET: "quiet",
    FanSpeedLevel.NORMAL: "standard",
    FanSpeedLevel.MAX: "strong",
    FanSpeedLevel.MAX_PLUS: "max",
}


class SetFanSpeedNgiot(JsonCommandWithMessageHandling):
    """Set fan speed via ngiot ``apn=50011``.

    Used by devices whose firmware rejects the standard devmanager ``setSpeed``
    command, routing fan speed changes through the ngiot endpoint instead.
    """

    NAME = "set_fan_speed_ngiot"

    def __init__(self, speed: FanSpeedLevel | str) -> None:
        """Initialise with the desired fan speed level."""
        if isinstance(speed, str):
            speed = get_enum(FanSpeedLevel, speed)
        self._speed = speed
        super().__init__()

    def _get_payload(self) -> dict[str, Any]:
        """Return empty payload — request is built in ``_execute_api_request``."""
        return {}

    async def _execute_api_request(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        """POST the fan speed change to the ngiot endpoint."""
        did = device_info["did"]
        mid = device_info["class"]
        res = device_info["resource"]
        fan_mode = _FAN_LEVEL_TO_MODE.get(self._speed, "standard")

        credentials = await authenticator.authenticate()
        async with aiohttp.ClientSession() as session:
            sst = await get_sst(
                session,
                token=credentials.token,
                user_id=credentials.user_id,
                did=did,
                mid=mid,
            )
            resp = await ngiot_post(
                session,
                sst=sst, eid=did, et=mid, er=res,
                apn="50011",
                body_data={"fanMode": fan_mode},
            )
        return {"ret": "ok", "ngiot": resp}

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        """No-op — response handled in ``_handle_response``."""
        return HandlingResult.success()

    def _handle_response(
        self,
        event_bus: EventBus,
        response: dict[str, Any],
    ) -> HandlingResult:
        """Fire FanSpeedEvent after a successful speed change."""
        if response.get("ret") == "ok":
            event_bus.notify(FanSpeedEvent(self._speed))
            return HandlingResult.success()
        _LOGGER.warning("SetFanSpeedNgiot failed: %s", response)
        return HandlingResult(HandlingState.FAILED)
