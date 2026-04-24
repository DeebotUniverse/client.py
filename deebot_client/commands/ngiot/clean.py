"""Clean commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import StateEvent
from deebot_client.exceptions import ApiError
from deebot_client.message import HandlingResult
from deebot_client.models import CleanAction, CleanMode, State
from deebot_client.ngiot_client import NgiotRequest

from .common import (
    APN_AREA_CLEAN,
    APN_CLEAN_START,
    APN_PAUSE,
    APN_RESUME,
    APN_RETURN_TO_DOCK,
    NgiotExecuteCommand,
    RobotDetailGetCommand,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from deebot_client.authentication import Authenticator
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo
    from deebot_client.ngiot_client import NgiotClient

_ACTIVE_WORK_MODES = {
    "smart",
    "smartclean",
    "area",
    "auto",
    "customarea",
    "custom_area",
    "spotarea",
    "spot_area",
}


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "on", "yes"}
    return False


def map_snapshot_state(data: Mapping[str, Any]) -> State:
    """Map robot-detail snapshot fields onto the generic state enum."""
    work_mode = str(data.get("workMode", "")).strip().lower()
    pause_switch = data.get("pauseSwitch")
    charge_status = _coerce_bool(data.get("chargeStatus"))

    if work_mode == "auto_pause" or (
        pause_switch is True and work_mode in _ACTIVE_WORK_MODES
    ):
        return State.PAUSED
    if work_mode in {"gocharge", "go_charge"}:
        return State.RETURNING
    if charge_status and work_mode in {"stop", "idle", "", "none"}:
        return State.DOCKED
    if charge_status:
        return State.RETURNING
    if work_mode in _ACTIVE_WORK_MODES:
        return State.CLEANING
    return State.IDLE


def map_live_state(
    data: Mapping[str, Any], previous: State | None = None
) -> State | None:
    """Map live status events onto the generic state enum."""
    status = str(data.get("status", "")).strip().lower()
    pause_switch = data.get("pauseSwitch")
    mapped_state = {
        "smartclean": State.PAUSED if pause_switch is True else State.CLEANING,
        "gocharge": State.RETURNING,
        "go_charge": State.RETURNING,
        "idle": State.DOCKED if _coerce_bool(data.get("chargeStatus")) else State.IDLE,
    }.get(status)

    if mapped_state is not None:
        return mapped_state

    if pause_switch is True and previous in {State.CLEANING, State.PAUSED}:
        return State.PAUSED

    resume_from_pause = pause_switch is False and previous == State.PAUSED
    if resume_from_pause:
        return State.CLEANING

    return (
        map_snapshot_state(data)
        if any(key in data for key in ("workMode", "chargeStatus"))
        else None
    )


class Clean(NgiotExecuteCommand):
    """Translate generic clean actions into NGIOT control payloads."""

    NAME = "clean"

    def __init__(self, action: CleanAction) -> None:
        super().__init__({})
        self._action = action

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[HandlingResult, dict[str, Any]]:
        state = event_bus.get_last_event(StateEvent)
        if state is not None and self._action is CleanAction.RESUME:
            if state.state != State.PAUSED:
                self._action = CleanAction.START
        elif state is not None and self._action is CleanAction.START:
            if state.state == State.PAUSED:
                self._action = CleanAction.RESUME

        return await super()._execute(authenticator, device_info, event_bus)

    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        apn, body_data = self._get_request()
        return await client.request(
            device_info,
            NgiotRequest(apn=apn, body_data=body_data),
        )

    def _get_request(self) -> tuple[str, dict[str, Any]]:
        requests: dict[CleanAction, tuple[str, dict[str, Any]]] = {
            CleanAction.START: (
                APN_CLEAN_START,
                {"cleanSwitch": True, "cleanMode": "smart"},
            ),
            CleanAction.PAUSE: (APN_PAUSE, {"pauseSwitch": True}),
            CleanAction.RESUME: (APN_RESUME, {"pauseSwitch": False}),
            CleanAction.STOP: (APN_RETURN_TO_DOCK, {"chargeSwitch": True}),
        }
        try:
            return requests[self._action]
        except KeyError as ex:
            msg = f"Unsupported clean action: {self._action}"
            raise ApiError(msg) from ex


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
        if self._mode is not CleanMode.SPOT_AREA:
            msg = "NGIOT area cleaning currently supports room-id cleaning only"
            raise ApiError(msg)

        if self._cleanings != 1:
            msg = "NGIOT room cleaning repeat count has not been captured yet"
            raise ApiError(msg)

        return await client.request(
            device_info,
            NgiotRequest(
                apn=APN_AREA_CLEAN,
                body_data={
                    "cleanSwitch": True,
                    "cleanMode": "area",
                    "cleanValues": self._room_ids,
                },
            ),
        )


class GetCleanInfo(RobotDetailGetCommand):
    """Get high-level robot state."""

    NAME = "getCleanInfo"
    FIELDS = ("cleanValues", "workMode", "chargeStatus", "pauseSwitch")

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus: EventBus,
        data: dict[str, Any],
    ) -> HandlingResult:
        event_bus.notify(StateEvent(map_snapshot_state(data)))
        return HandlingResult.success()
