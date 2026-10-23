"""Native numeric control commands (Y1 Pro cqyi87).

Stop (40013) ends the cleaning task and returns to dock.
Pause (40009) halts in place.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any, assert_never

from deebot_client.command import Command, InitParam
from deebot_client.events import FanSpeedLevel, LifeSpan, StateEvent
from deebot_client.events.water_info import WaterAmount
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import CleanAction, State
from deebot_client.util import get_enum

from .custom import CustomCommand
from .life_span import ResetLifeSpan
from .native_common import (
    NativeExecuteCommand,
    NativeJsonCommand,
    NativeSetCommand,
    native_header,
)
from .native_info import GetNativeInfo

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo

_FAN_TO_NATIVE: dict[FanSpeedLevel, str] = {
    FanSpeedLevel.QUIET: "quiet",
    FanSpeedLevel.NORMAL: "auto",
    FanSpeedLevel.MAX: "strong",
    FanSpeedLevel.MAX_PLUS: "max",
}
_FAN_FROM_NATIVE: dict[str, FanSpeedLevel] = {
    native: level for level, native in _FAN_TO_NATIVE.items()
}

_WATER_TO_NATIVE: dict[WaterAmount, str] = {
    WaterAmount.LOW: "low",
    WaterAmount.MEDIUM: "mid",
    WaterAmount.HIGH: "high",
}
_WATER_FROM_NATIVE: dict[str, WaterAmount] = {
    native: amount for amount, native in _WATER_TO_NATIVE.items()
}

_RESET_TO_NATIVE: dict[LifeSpan, str] = {
    LifeSpan.BRUSH: "rollBrush",
    LifeSpan.FILTER: "filter",
    LifeSpan.SIDE_BRUSH: "sideBrush",
    LifeSpan.UNIT_CARE: "unitCare",
}
_RESET_FROM_NATIVE: dict[str, LifeSpan] = {
    native: component for component, native in _RESET_TO_NATIVE.items()
}


class NativeStartClean(NativeExecuteCommand):
    """Start smart cleaning."""

    NAME = "40001"

    def __init__(self) -> None:
        super().__init__({"cleanSwitch": True, "cleanMode": "smart"})

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[HandlingResult, dict[str, Any]]:
        """Execute command, resuming when paused."""
        state = event_bus.get_last_event(StateEvent)
        if isinstance(state, StateEvent) and state.state == State.PAUSED:
            return await NativeResumeClean()._execute(  # noqa: SLF001
                authenticator, device_info, event_bus
            )
        return await super()._execute(authenticator, device_info, event_bus)


class NativePauseClean(NativeExecuteCommand):
    """Pause cleaning, halting in place."""

    NAME = "40009"

    def __init__(self) -> None:
        super().__init__({"pauseSwitch": True})


class NativeResumeClean(NativeExecuteCommand):
    """Resume cleaning."""

    NAME = "40011"

    def __init__(self) -> None:
        super().__init__({"pauseSwitch": False})

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[HandlingResult, dict[str, Any]]:
        """Execute command, starting when not paused."""
        state = event_bus.get_last_event(StateEvent)
        if isinstance(state, StateEvent) and state.state != State.PAUSED:
            return await NativeStartClean()._execute(  # noqa: SLF001
                authenticator, device_info, event_bus
            )
        return await super()._execute(authenticator, device_info, event_bus)


class NativeReturnToDock(NativeExecuteCommand):
    """Return to dock, ending the task (also serves as Stop)."""

    NAME = "40013"

    def __init__(self) -> None:
        super().__init__({"chargeSwitch": True})


class NativeLocate(NativeExecuteCommand):
    """Locate the bot (play sound)."""

    NAME = "40019"

    def __init__(self) -> None:
        super().__init__({"seek": True})


class NativeResetLifeSpan(NativeJsonCommand, ResetLifeSpan):
    """Adapt reset serialization while sharing ACK and P2P refresh handling."""

    NAME = "50017"
    _mqtt_params = MappingProxyType(
        {"resetConsumable": InitParam(LifeSpan, "life_span")}
    )

    def __init__(self, life_span: LifeSpan) -> None:
        if life_span not in _RESET_TO_NATIVE:
            msg = f"Unsupported native reset component: {life_span}"
            raise ValueError(msg)
        super().__init__(life_span)
        self._args = {"resetConsumable": _RESET_TO_NATIVE[life_span]}

    @classmethod
    def _decode(cls, type_: type, value: Any) -> Any:
        if type_ is LifeSpan and isinstance(value, str):
            if value in _RESET_FROM_NATIVE:
                return _RESET_FROM_NATIVE[value]
            msg = f'Could not convert "{value}" into {type_}'
            raise ValueError(msg)
        return super()._decode(type_, value)

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> HandlingResult:
        """Handle response, refreshing consumables on success."""
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            result.requested_commands.append(GetNativeInfo(["consumables"]))
        return result


class NativeSetFanSpeed(NativeSetCommand):
    """Set native fan speed."""

    NAME = "50011"
    get_command = GetNativeInfo
    _mqtt_params = MappingProxyType({"fanMode": InitParam(FanSpeedLevel, "speed")})

    def __init__(self, speed: FanSpeedLevel | str) -> None:
        if isinstance(speed, str):
            speed = get_enum(FanSpeedLevel, speed)
        super().__init__({"fanMode": _FAN_TO_NATIVE[speed]})

    @classmethod
    def _decode(cls, type_: type, value: Any) -> Any:
        if type_ is FanSpeedLevel and isinstance(value, str):
            if value in _FAN_FROM_NATIVE:
                return _FAN_FROM_NATIVE[value]
            msg = f'Could not convert "{value}" into {type_}'
            raise ValueError(msg)
        return super()._decode(type_, value)


class NativeSetWaterAmount(NativeSetCommand):
    """Set native water amount."""

    NAME = "50013"
    get_command = GetNativeInfo
    _mqtt_params = MappingProxyType({"waterMode": InitParam(WaterAmount, "amount")})

    def __init__(self, amount: WaterAmount | str) -> None:
        if isinstance(amount, str):
            amount = get_enum(WaterAmount, amount)
        if amount not in _WATER_TO_NATIVE:
            msg = f"Unsupported native water amount: {amount}"
            raise ValueError(msg)
        super().__init__({"waterMode": _WATER_TO_NATIVE[amount]})

    @classmethod
    def _decode(cls, type_: type, value: Any) -> Any:
        if type_ is WaterAmount and isinstance(value, str):
            if value in _WATER_FROM_NATIVE:
                return _WATER_FROM_NATIVE[value]
            msg = f'Could not convert "{value}" into {type_}'
            raise ValueError(msg)
        return super()._decode(type_, value)


class NativeCustomCommand(CustomCommand, NativeJsonCommand):
    """Custom command using the native header."""

    def _get_payload(self) -> dict[str, Any] | list[Any]:
        payload: dict[str, Any] = {"header": native_header()}
        if len(self._args) > 0:
            payload["body"] = {"data": self._args}
        return payload


def native_clean(action: CleanAction) -> Command:
    """Create the native clean command for the given action."""
    match action:
        case CleanAction.START:
            return NativeStartClean()
        case CleanAction.PAUSE:
            return NativePauseClean()
        case CleanAction.RESUME:
            return NativeResumeClean()
        case CleanAction.STOP:
            return NativeReturnToDock()
        case _:
            assert_never(action)
