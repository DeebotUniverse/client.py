"""Native numeric info messages (Y1 Pro 10000 partial reports)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from deebot_client.events import (
    BatteryEvent,
    FanSpeedEvent,
    FanSpeedLevel,
    StateEvent,
)
from deebot_client.events.base import Event
from deebot_client.events.water_info import (
    MopAttachedEvent,
    WaterAmount,
    WaterAmountEvent,
)
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import State

from .native_settings import handle_native_settings
from .native_telemetry import (
    handle_clean_stats,
    handle_consumables,
    handle_device_info,
    handle_error,
)

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_FAN_MODE_MAP: dict[str, FanSpeedLevel] = {
    "quiet": FanSpeedLevel.QUIET,
    "auto": FanSpeedLevel.NORMAL,
    "strong": FanSpeedLevel.MAX,
    "max": FanSpeedLevel.MAX_PLUS,
}

_WATER_MODE_MAP: dict[str, WaterAmount] = {
    "low": WaterAmount.LOW,
    "mid": WaterAmount.MEDIUM,
    "high": WaterAmount.HIGH,
}

_CLEAN_STATUSES = frozenset({"smartclean", "areaclean", "zoneclean"})
_SUPPORTED_STATUSES = _CLEAN_STATUSES | {"gocharge", "idle"}


@dataclass(frozen=True)
class NativeInfoEvent(Event):
    """Merged native status/charge/pause snapshot.

    Cached per EventBus via EventBus last-event storage, giving per-device
    merge without global class state. Internal only; not a public capability.
    """

    status: str | None = None
    charge_status: bool | None = None
    pause_switch: bool | None = None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return value == 1
    return None


def _last_native_info(event_bus: EventBus) -> NativeInfoEvent | None:
    last = event_bus.get_last_event(NativeInfoEvent)
    return last if isinstance(last, NativeInfoEvent) else None


def _derive_state(
    status: str | None, charge: bool | None, pause: bool | None
) -> State | None:
    if status is None:
        return None
    lowered = status.lower()
    if lowered in _CLEAN_STATUSES:
        if pause is True:
            result: State | None = State.PAUSED
        elif pause is False:
            result = State.CLEANING
        else:
            result = None
    elif lowered == "gocharge":
        result = State.RETURNING
    elif lowered == "idle":
        result = State.DOCKED if charge is True else State.IDLE
    else:
        result = None
    return result


def _parse_status(raw: Any) -> tuple[str | None, bool]:
    if not isinstance(raw, str):
        return None, False
    lowered = raw.lower()
    if lowered in _SUPPORTED_STATUSES:
        return raw, False
    return None, lowered != "none"


def _notify_settings(event_bus: EventBus, data: dict[str, Any]) -> None:
    if "fanMode" in data:
        fan_mode = data["fanMode"]
        if isinstance(fan_mode, str) and fan_mode in _FAN_MODE_MAP:
            event_bus.notify(FanSpeedEvent(_FAN_MODE_MAP[fan_mode]))

    if "waterMode" in data:
        water_mode = data["waterMode"]
        if isinstance(water_mode, str) and water_mode in _WATER_MODE_MAP:
            event_bus.notify(WaterAmountEvent(_WATER_MODE_MAP[water_mode]))

    if data.get("mopState") == "installed":
        event_bus.notify(MopAttachedEvent(True))

    handle_native_settings(event_bus, data)


class OnNativeInfo(MessageBodyDataDict):
    """On native info message (numeric 10000 partial reports)."""

    NAME = "10000"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if not isinstance(data, dict) or not data:
            return HandlingResult.success()

        status, status_clears_cache = _parse_status(data.get("status"))
        pause = _as_bool(data.get("pauseSwitch")) if "pauseSwitch" in data else None
        charge = _as_bool(data.get("chargeStatus")) if "chargeStatus" in data else None

        if "battery" in data:
            battery = data["battery"]
            if (
                isinstance(battery, bool)
                or not isinstance(battery, int)
                or not 0 <= battery <= 100
            ):
                return HandlingResult.analyse()
            event_bus.notify(BatteryEvent(battery))

        _notify_settings(event_bus, data)

        if "consumables" in data:
            handle_consumables(event_bus, data["consumables"])

        if "deviceInfo" in data:
            handle_device_info(event_bus, data["deviceInfo"])

        if "error" in data:
            handle_error(event_bus, data["error"])

        if "cleanArea" in data or "cleanTime" in data:
            handle_clean_stats(event_bus, data)

        last = _last_native_info(event_bus)
        if status is not None:
            merged_status: str | None = status
        elif status_clears_cache:
            merged_status = None
        else:
            merged_status = last.status if last else None
        merged_pause = (
            pause if pause is not None else (last.pause_switch if last else None)
        )
        merged_charge = (
            charge if charge is not None else (last.charge_status if last else None)
        )

        state = _derive_state(merged_status, merged_charge, merged_pause)
        if (
            state is not None
            and not status_clears_cache
            and (status is not None or pause is not None or charge is not None)
        ):
            event_bus.notify(StateEvent(state))

        if (
            status is not None
            or status_clears_cache
            or pause is not None
            or charge is not None
        ):
            event_bus.notify(
                NativeInfoEvent(
                    status=merged_status,
                    charge_status=merged_charge,
                    pause_switch=merged_pause,
                )
            )

        return HandlingResult.success()
