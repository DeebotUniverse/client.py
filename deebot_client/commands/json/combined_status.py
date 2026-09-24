"""Combined status command for devices using cmdName ``10001``."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, ClassVar

from deebot_client.events import (
    BatteryEvent,
    ChildLockEvent,
    ErrorEvent,
    FanSpeedEvent,
    LifeSpan,
    LifeSpanEvent,
    OtaEvent,
    StateEvent,
)
from deebot_client.events.fan_speed import FanSpeedLevel
from deebot_client.events.water_info import MopAttachedEvent, WaterAmount, WaterAmountEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import State

from .common import JsonCommandWithMessageHandling

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo

_LOGGER = get_logger(__name__)

_ALL_STATUS_FIELDS: list[str] = [
    "stationType", "stationStatus", "cleanValues", "chargeStatus",
    "pauseSwitch", "battery", "disturbSwitch", "disturbTimeSet",
    "mopState", "workMode", "breakCleanStatus", "fanMode", "waterMode",
    "cleanCount", "error", "consumables", "newMapReport",
    "expandedMapReport", "cleanLogReport", "deviceInfo", "childLock",
    "isEurope", "cleanTime", "cleanArea", "silentOtaSwitch",
    "nextSchedule", "dormant", "relocateSwitch", "unitSet", "otaData",
    "voiceData", "timeZone",
]

_CONSUMABLE_MAP: dict[str, LifeSpan] = {
    "sideBrush": LifeSpan.SIDE_BRUSH,
    "unitCare": LifeSpan.UNIT_CARE,
    "rollBrush": LifeSpan.BRUSH,
    "filter": LifeSpan.FILTER,
}

_FAN_MODE_MAP: dict[str, FanSpeedLevel] = {
    "quiet": FanSpeedLevel.QUIET,
    "standard": FanSpeedLevel.NORMAL,
    "strong": FanSpeedLevel.MAX,
    "max": FanSpeedLevel.MAX_PLUS,
    "auto": FanSpeedLevel.NORMAL,
}

_WATER_MODE_MAP: dict[str, WaterAmount] = {
    "low": WaterAmount.LOW,
    "medium": WaterAmount.MEDIUM,
    "high": WaterAmount.HIGH,
    "ultrahigh": WaterAmount.ULTRAHIGH,
}


class GetCombinedStatus(JsonCommandWithMessageHandling):
    """Get all device status fields in a single combined call (cmdName ``10001``).

    Used by devices whose firmware does not respond to the standard individual
    commands (``getBattery``, ``getChargeState``, ``getCleanInfo``, etc.) but
    instead returns battery, state, fan speed, consumables and more in one call.

    A short-lived class-level cache (keyed by device id) avoids redundant
    network calls when multiple capabilities request a refresh in the same
    poll cycle.
    """

    NAME = "10001"
    CACHE_SECONDS = 5.0

    _cache: ClassVar[dict[str, tuple[float, dict[str, Any]]]] = {}

    def __init__(
        self,
        fields: list[str] | None = None,
        *,
        is_available_check: bool = False,
    ) -> None:
        """Initialise the command, optionally restricting the requested fields."""
        if fields is None:
            fields = _ALL_STATUS_FIELDS
        self._is_available_check = is_available_check
        super().__init__({"fields": fields})

    def _get_payload(self) -> dict[str, Any]:
        """Build payload matching the real app's captured header format."""
        return {
            "header": {
                "channel": "iOS",
                "reqid": "neo2py",
                "ts": str(int(time.time() * 1000)),
                "ver": "0.0.50",
                "m": "request",
                "pri": 1,
                "tzm": 600,
                "tzc": "Australia/Melbourne",
            },
            "body": {"data": self._args},
        }

    async def _execute_api_request(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        """Execute the API request, reusing a cached response when available."""
        device_id = device_info.get("did", "")
        now = time.monotonic()
        cached = GetCombinedStatus._cache.get(device_id)
        if cached is not None:
            cached_time, cached_response = cached
            if now - cached_time < self.CACHE_SECONDS:
                return cached_response

        response = await super()._execute_api_request(authenticator, device_info)
        GetCombinedStatus._cache[device_id] = (now, response)
        return response

    @classmethod
    def _handle_body(
        cls,
        event_bus: EventBus,
        body: dict[str, Any],
    ) -> HandlingResult:
        """Parse the combined status response and fire events for known fields."""
        data = body.get("data")
        if not isinstance(data, dict):
            return HandlingResult(HandlingState.ANALYSE)

        if "battery" in data and data["battery"] is not None:
            event_bus.notify(BatteryEvent(data["battery"]))

        charge_status = data.get("chargeStatus")
        pause_switch = data.get("pauseSwitch")
        error_list = data.get("error")
        work_mode = data.get("workMode")

        state: State | None = None
        if error_list and error_list != [0]:
            state = State.ERROR
        elif charge_status is True:
            state = State.DOCKED
        elif pause_switch is True:
            state = State.PAUSED
        elif charge_status is False:
            state = State.CLEANING if work_mode and work_mode != "stop" else State.IDLE

        if state is not None:
            _LOGGER.debug("GetCombinedStatus derived state: %s", state)
            event_bus.notify(StateEvent(state))

        consumables = data.get("consumables")
        if isinstance(consumables, list):
            for item in consumables:
                item_type = item.get("type")
                life_span_type = _CONSUMABLE_MAP.get(item_type)
                if life_span_type is None:
                    _LOGGER.debug("Unmapped consumable type — skipping LifeSpanEvent")
                    continue
                left = item.get("left")
                total = item.get("total")
                if left is None or total is None or total == 0:
                    continue
                event_bus.notify(
                    LifeSpanEvent(
                        type=life_span_type,
                        percent=(left / total) * 100,
                        remaining=int(left),
                    )
                )

        if isinstance(error_list, list) and error_list:
            error_code = error_list[0]
            event_bus.notify(
                ErrorEvent(
                    code=error_code,
                    description="No error" if error_code == 0 else None,
                )
            )

        fan_mode = data.get("fanMode")
        if fan_mode is not None:
            fan_level = _FAN_MODE_MAP.get(fan_mode)
            if fan_level is not None:
                event_bus.notify(FanSpeedEvent(fan_level))
            else:
                _LOGGER.debug("Unmapped fanMode — skipping FanSpeedEvent")

        water_mode = data.get("waterMode")
        if water_mode is not None:
            water_amount = _WATER_MODE_MAP.get(water_mode)
            if water_amount is not None:
                event_bus.notify(WaterAmountEvent(water_amount))
            else:
                _LOGGER.debug("Unmapped waterMode — skipping WaterAmountEvent")

        mop_state = data.get("mopState")
        if mop_state is not None:
            if mop_state == "none":
                event_bus.notify(MopAttachedEvent(attached=False))
            else:
                _LOGGER.debug("Non-null mopState — treating as mop attached")
                event_bus.notify(MopAttachedEvent(attached=True))

        child_lock = data.get("childLock")
        if child_lock is not None:
            event_bus.notify(ChildLockEvent(enabled=bool(child_lock)))

        ota_data = data.get("otaData")
        silent_ota_switch = data.get("silentOtaSwitch")
        if ota_data is not None or silent_ota_switch is not None:
            ota_info = (ota_data or {}).get("otaInfo") or {}
            version = ota_info.get("ver") or None
            event_bus.notify(
                OtaEvent(
                    support_auto=True,
                    auto_enabled=silent_ota_switch,
                    version=version if version else None,
                    status=(ota_data or {}).get("otaStatus"),
                    progress=ota_info.get("progress"),
                )
            )

        return HandlingResult.success()
