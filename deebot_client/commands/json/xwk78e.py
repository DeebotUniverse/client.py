"""China T80-specific commands."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.commands.json.auto_empty import SetAutoEmpty
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.clean import CleanV2
from deebot_client.commands.json.clean_preference import (
    GetCleanPreference,
    SetCleanPreference,
)
from deebot_client.commands.json.common import (
    ExecuteCommand,
    JsonCommandWithMessageHandling,
    JsonGetCommand,
    JsonSetCommand,
)
from deebot_client.commands.json.station_action import StationAction
from deebot_client.events import (
    CleanCountEvent,
    FanSpeedEvent,
    StateEvent,
    TrueDetectEvent,
    WorkModeEvent,
)
from deebot_client.events.auto_empty import Frequency
from deebot_client.events.water_info import WaterCustomAmountEvent
from deebot_client.events.xwk78e import (
    AutoEmptyEventT80,
    AutoEmptyIntensity,
    TrueDetectLevel,
    TrueDetectLevelEvent,
    WashMode,
    WashModeEvent,
)
from deebot_client.message import HandlingResult
from deebot_client.messages.json.xwk78e import (
    OnAutoEmptyT80,
    OnWashInfoT80,
    OnWorkStateT80,
)
from deebot_client.models import CleanAction, CleanMode, State
from deebot_client.util import get_enum

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.commands import StationAction as StationActionType
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo


class SetAutoEmptyV2(SetAutoEmpty):
    """China T80 auto-empty command."""

    def __init__(
        self,
        enable: bool | None = None,
        frequency: Frequency | str | None = None,
        intensity: AutoEmptyIntensity | int | str | None = None,
    ) -> None:
        if isinstance(frequency, str):
            frequency = get_enum(Frequency, frequency)
        if isinstance(intensity, str):
            intensity = get_enum(AutoEmptyIntensity, intensity)
        if intensity is not None:
            intensity = AutoEmptyIntensity(intensity)
        self._requested_frequency = frequency
        self._requested_intensity = intensity
        ExecuteCommand.__init__(
            self,
            {
                "enable": int(enable) if enable is not None else 1,
                "frequency": frequency.value if frequency else Frequency.SMART.value,
                "intensity": int(intensity) if intensity is not None else 1,
            },
        )

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[Any, dict[str, Any]]:
        event = event_bus.get_last_event(AutoEmptyEventT80)
        if isinstance(event, AutoEmptyEventT80):
            if self._requested_frequency is None and event.frequency:
                self._args["frequency"] = event.frequency.value
            if self._requested_intensity is None and event.intensity is not None:
                self._args["intensity"] = int(event.intensity)
        return await super()._execute(authenticator, device_info, event_bus)


class GetAutoEmptyT80(OnAutoEmptyT80, JsonCommandWithMessageHandling):
    """Get T80 auto-empty state and suction intensity."""

    NAME = "getAutoEmpty"


class SetWashInfoT80(JsonSetCommand):
    """Set T80 station mop-washing mode."""

    NAME = "setWashInfo"
    _mqtt_params = MappingProxyType(
        {
            "mode": InitParam(int),
            "interval": InitParam(int, optional=True),
        }
    )

    @property
    def get_command(self) -> type[GetWashInfoT80]:
        """Return the T80 wash-info query command."""
        return GetWashInfoT80

    def __init__(self, mode: WashMode | int | str, interval: int = 15) -> None:
        if isinstance(mode, str):
            mode = get_enum(WashMode, mode)
        self._requested_interval = interval
        super().__init__({"mode": int(mode), "interval": interval})

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[Any, dict[str, Any]]:
        event = event_bus.get_last_event(WashModeEvent)
        if isinstance(event, WashModeEvent) and event.interval is not None:
            self._args["interval"] = event.interval
        return await super()._execute(authenticator, device_info, event_bus)


class GetWashInfoT80(OnWashInfoT80, JsonGetCommand):
    """Get T80 station mop-washing mode."""

    NAME = "getWashInfo"


class GetTrueDetectT80(JsonGetCommand):
    """Get T80 obstacle detection state and sensitivity."""

    NAME = "getTrueDetect"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        try:
            level = TrueDetectLevel(data["level"])
        except (KeyError, ValueError):
            return HandlingResult.analyse()
        event_bus.notify(TrueDetectEvent(bool(data["enable"])))
        event_bus.notify(TrueDetectLevelEvent(level))
        return HandlingResult.success()


class SetTrueDetectV2(JsonSetCommand):
    """China T80 AIVI 3D setting command."""

    NAME = "setTrueDetect"

    _mqtt_params = MappingProxyType(
        {
            "enable": InitParam(bool),
            "level": InitParam(int),
        }
    )

    def __init__(self, enable: bool, level: int = 1) -> None:
        JsonSetCommand.__init__(self, {"enable": int(enable), "level": level})

    @property
    def get_command(self) -> type[GetTrueDetectT80]:
        """Return the T80 true-detect query command."""
        return GetTrueDetectT80


class SetTrueDetectLevelT80(JsonSetCommand):
    """Set only the T80 obstacle detection sensitivity."""

    NAME = "setTrueDetect"
    _mqtt_params = MappingProxyType(
        {
            "enable": InitParam(bool),
            "level": InitParam(int),
        }
    )

    def __init__(
        self, level: TrueDetectLevel | int | str, enable: bool | None = None
    ) -> None:
        if isinstance(level, str):
            level = get_enum(TrueDetectLevel, level)
        self._requested_level = TrueDetectLevel(level)
        super().__init__(
            {
                "enable": int(enable) if enable is not None else 1,
                "level": int(self._requested_level),
            }
        )

    @property
    def get_command(self) -> type[GetTrueDetectT80]:
        """Return the T80 true-detect query command."""
        return GetTrueDetectT80

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[Any, dict[str, Any]]:
        event = event_bus.get_last_event(TrueDetectEvent)
        if isinstance(event, TrueDetectEvent):
            self._args["enable"] = int(event.enabled)
        return await super()._execute(authenticator, device_info, event_bus)


class StationActionT80(StationAction):
    """China T80 station action with explicit action verb."""

    def __init__(self, action: StationActionType, *, act: int = 1) -> None:
        ExecuteCommand.__init__(self, {"act": act, "type": action.value})


class ChargeT80(Charge):
    """T80 charge command preserving docked state on duplicate charge."""

    @classmethod
    def _handle_body(
        cls, event_bus: EventBus, body: dict[str, Any]
    ) -> Any:
        if int(body.get("code", -1)) == 0:
            state = event_bus.get_last_event(StateEvent)
            if state and state.state == State.DOCKED:
                event_bus.notify(StateEvent(State.DOCKED))
            else:
                event_bus.notify(StateEvent(State.RETURNING))
            return HandlingResult.success()
        return super()._handle_body(event_bus, body)


class GetWorkStateT80(OnWorkStateT80, JsonCommandWithMessageHandling):
    """T80 work-state refresh command."""

    NAME = "getWorkState"


class CleanAreaV2FreeClean(CleanV2):
    """T80 room-cleaning command using the freeClean payload."""

    def __init__(
        self, mode: CleanMode, area: list[int | float], cleanings: int = 1
    ) -> None:
        del mode
        self._room_ids = [int(room_id) for room_id in area]
        self._cleanings = cleanings
        self._additional_content = {
            "type": CleanMode.FREE_CLEAN.value,
            "value": ";".join(
                self._room_value(
                    room_id,
                    {
                        "cleanings": cleanings,
                        "fan_speed": 0,
                        "water_amount": 30,
                        "work_mode": 0,
                    },
                )
                for room_id in self._room_ids
            ),
        }
        super().__init__(CleanAction.START)

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[Any, dict[str, Any]]:
        """Use the current T80 cleaning settings in the room payload."""
        fan_speed = event_bus.get_last_event(FanSpeedEvent)
        water_amount = event_bus.get_last_event(WaterCustomAmountEvent)
        work_mode = event_bus.get_last_event(WorkModeEvent)
        clean_count = event_bus.get_last_event(CleanCountEvent)
        if not isinstance(fan_speed, FanSpeedEvent):
            fan_speed = None
        if not isinstance(water_amount, WaterCustomAmountEvent):
            water_amount = None
        if not isinstance(work_mode, WorkModeEvent):
            work_mode = None
        if not isinstance(clean_count, CleanCountEvent):
            clean_count = None
        if fan_speed or water_amount or work_mode or clean_count:
            settings = {
                "fan_speed": fan_speed.speed if fan_speed else 0,
                "water_amount": self._water_value(water_amount.value)
                if water_amount
                else 30,
                "work_mode": work_mode.mode if work_mode else 0,
                "cleanings": clean_count.count if clean_count else self._cleanings,
            }
            self._additional_content["value"] = ";".join(
                self._room_value(room_id, settings) for room_id in self._room_ids
            )
        self._args = self._get_args(CleanAction.START)
        return await super()._execute(authenticator, device_info, event_bus)

    @staticmethod
    def _water_value(custom_amount: int) -> int:
        """Convert T80 custom water percent to the freeClean scale."""
        return custom_amount * 2

    @staticmethod
    def _room_value(room_id: int, settings: dict[str, Any]) -> str:
        return (
            f"1,{room_id},,{settings['cleanings']},{settings['fan_speed']}"
            f",{settings['water_amount']},{settings['work_mode']},1,0"
        )

    def _get_args(self, action: CleanAction) -> dict[str, Any]:
        args = super()._get_args(action)
        if action == CleanAction.START:
            args["content"].update(self._additional_content)
        return args


class GetCleanPreferenceT80(GetCleanPreference):
    """T80 clean-preference read, whose device service is unavailable."""

    @classmethod
    def _handle_body(
        cls, event_bus: EventBus, body: dict[str, Any]
    ) -> Any:
        if body.get("code") == 20005:
            return HandlingResult.success()
        return super()._handle_body(event_bus, body)


class SetCleanPreferenceT80(SetCleanPreference):
    """T80 clean-preference setter linked to the T80 read command."""

    get_command = GetCleanPreferenceT80
