"""Clean commands."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from deebot_client.events import StateEvent
from deebot_client.exceptions import ApiError
from deebot_client.message import HandlingResult
from deebot_client.models import CleanAction, CleanMode, State
from deebot_client.ngiot_client import APN_AREA_CLEAN, APN_CLEAN_START, APN_PAUSE

from .common import NgiotExecuteCommand, RobotDetailGetCommand

if TYPE_CHECKING:
    from deebot_client.models import ApiDeviceInfo
    from deebot_client.ngiot_client import NgiotClient


class Clean(NgiotExecuteCommand):
    """Translate generic clean actions into captured NGIOT control payloads."""

    NAME = "clean"

    def __init__(self, action: CleanAction) -> None:
        super().__init__({})
        self._action = action

    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        apn, body_data = self._get_request()
        return await client.request(
            device_info,
            apn=apn,
            body_data=body_data,
        )

    def _get_request(self) -> tuple[str, dict[str, Any]]:
        if self._action is CleanAction.START:
            return APN_CLEAN_START, {"cleanSwitch": True, "cleanMode": "smart"}
        if self._action is CleanAction.PAUSE:
            return APN_PAUSE, {"pauseSwitch": True}
        if self._action is CleanAction.RESUME:
            return APN_RESUME, {"pauseSwitch": False}
        raise ApiError(
            "CleanAction.STOP payload has not been captured for NGIOT yet"
        )

class CleanArea(NgiotExecuteCommand):
    """Start room/area cleaning using room IDs."""

    NAME = "clean"

    def __init__(
        self,
        mode: CleanMode,
        area: list[int | float],
        cleanings: int = 1,
    ) -> None:
        super().__init__({})
        self._mode = mode
        self._room_ids = [int(value) for value in area]
        self._cleanings = cleanings

    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        if self._mode not in (CleanMode.CUSTOM_AREA, CleanMode.SPOT_AREA):
            raise ApiError(
                f"Clean mode {self._mode!s} is not mapped for NGIOT room cleaning"
            )

        if self._cleanings != 1:
            raise ApiError(
                "NGIOT room cleaning repeat count has not been captured yet"
            )

        return await client.request(
            device_info,
            apn=APN_AREA_CLEAN,
            body_data={
                "cleanSwitch": True,
                "cleanMode": "area",
                "cleanValues": self._room_ids,
            },
        )


class GetCleanInfo(RobotDetailGetCommand):
    """Get high-level robot state."""

    NAME = "getCleanInfo"
    FIELDS = ("chargeStatus", "pauseSwitch", "workMode", "error")

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus,
        data: dict[str, Any],
    ) -> HandlingResult:
        event_bus.notify(StateEvent(_map_state(data)))
        return HandlingResult.success()


def _extract_first_int(value: Any) -> int:
    if isinstance(value, list) and value:
        value = value[0]
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _map_state(data: Mapping[str, Any]) -> State:
    if _extract_first_int(data.get("error")) != 0:
        return State.ERROR
    if bool(data.get("pauseSwitch")):
        return State.PAUSED

    work_mode = str(data.get("workMode", "")).lower()
    charge_status = bool(data.get("chargeStatus"))

    if charge_status and work_mode in {"stop", "idle", "", "none"}:
        return State.DOCKED
    if charge_status:
        return State.RETURNING
    if work_mode in {"smart", "area", "auto", "customarea", "spotarea"}:
        return State.CLEANING
    return State.IDLE