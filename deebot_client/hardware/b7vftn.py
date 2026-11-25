"""DEEBOT T90 MAX PLUS OMNI Capabilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.capabilities import (
    Capabilities,
    CapabilityClean,
    CapabilityCleanAction,
    CapabilityCustomCommand,
    CapabilityEvent,
    CapabilityExecute,
    CapabilityExecuteTypes,
    CapabilityLifeSpan,
    CapabilityMap,
    CapabilityNumber,
    CapabilitySet,
    CapabilitySetEnable,
    CapabilitySettings,
    CapabilitySetTypes,
    CapabilityStation,
    CapabilityStats,
    CapabilityWater,
    DeviceType,
)
from deebot_client.commands import StationAction
from deebot_client.commands.json import station_action
from deebot_client.commands.json.auto_empty import GetAutoEmpty, SetAutoEmpty
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.child_lock import GetChildLock, SetChildLock
from deebot_client.commands.json.clean import Clean, CleanAreaV2, CleanV2
from deebot_client.commands.json.clean_count import GetCleanCount, SetCleanCount
from deebot_client.commands.json.clean_logs import GetCleanLogs
from deebot_client.commands.json.continuous_cleaning import (
    GetContinuousCleaning,
    SetContinuousCleaning,
)
from deebot_client.commands.json.custom import CustomCommand
from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.fan_speed import GetFanSpeed, SetFanSpeed
from deebot_client.commands.json.life_span import GetLifeSpan, ResetLifeSpan
from deebot_client.commands.json.map import (
    GetCachedMapInfo,
    GetMapInfoV2,
    GetMapSetV2,
    GetMapTrace,
)
from deebot_client.commands.json.mop_auto_wash_frequency import (
    GetMopAutoWashFrequency,
    SetMopAutoWashFrequency,
)
from deebot_client.commands.json.network import GetNetInfo
from deebot_client.commands.json.ota import GetOta, SetOta
from deebot_client.commands.json.play_sound import PlaySound
from deebot_client.commands.json.pos import GetPos
from deebot_client.commands.json.relocation import SetRelocationState
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.commands.json.sweep_mode import GetSweepMode, SetSweepMode
from deebot_client.commands.json.true_detect import GetTrueDetect, SetTrueDetect
from deebot_client.commands.json.voice_assistant_state import (
    GetVoiceAssistantState,
    SetVoiceAssistantState,
)
from deebot_client.commands.json.volume import GetVolume, SetVolume
from deebot_client.commands.json.water_info import GetWaterInfo, SetWaterInfo
from deebot_client.commands.json.work_mode import GetWorkMode, SetWorkMode
from deebot_client.commands.json.work_state import GetWorkState
from deebot_client.const import DataType
from deebot_client.events import (
    AvailabilityEvent,
    BatteryEvent,
    CachedMapInfoEvent,
    ChildLockEvent,
    CleanCountEvent,
    CleanLogEvent,
    ContinuousCleaningEvent,
    CustomCommandEvent,
    ErrorEvent,
    FanSpeedEvent,
    FanSpeedLevel,
    LifeSpan,
    LifeSpanEvent,
    MapChangedEvent,
    MapTraceEvent,
    NetworkInfoEvent,
    OtaEvent,
    PositionsEvent,
    ReportStatsEvent,
    RoomsEvent,
    StateEvent,
    StationEvent,
    StatsEvent,
    SweepModeEvent,
    TotalStatsEvent,
    TrueDetectEvent,
    VoiceAssistantStateEvent,
    VolumeEvent,
    WorkMode,
    WorkModeEvent,
    auto_empty,
    water_info,
)
from deebot_client.events.auto_empty import AutoEmptyEvent
from deebot_client.events.mop_auto_wash_frequency import MopAutoWashFrequencyEvent
from deebot_client.models import CleanAction, CleanMode, StaticDeviceInfo

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.command import Command
    from deebot_client.event_bus import EventBus
    from deebot_client.message import HandlingResult
    from deebot_client.models import ApiDeviceInfo


class _CleanRoomsV2(CleanV2):
    """Clean rooms with clean_V2 freeClean.

    This firmware rejects spotArea (20011 unknown type). The official app
    sends freeClean with one "1,<room id>" block per room, joined by ";".
    The leading 1 is the element type (room), not the number of passes;
    the passes are a robot setting (setCleanCount).
    """

    def __init__(self, rooms: list[int | float]) -> None:
        self._rooms_content = {
            "type": CleanMode.FREE_CLEAN.value,
            "value": ";".join(f"1,{int(room)}" for room in rooms),
        }
        super().__init__(CleanAction.START)

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[HandlingResult, dict[str, Any]]:
        # Always send "start": while paused, Clean._execute would turn it
        # into a bare "resume" and drop the rooms.
        return await super(Clean, self)._execute(authenticator, device_info, event_bus)

    def _get_args(self, action: CleanAction) -> dict[str, Any]:
        args = super()._get_args(action)
        if action == CleanAction.START:
            args["content"].update(self._rooms_content)
        return args


def _clean_area(
    mode: CleanMode, area: list[int | float], cleanings: int = 1
) -> Command:
    """Clean rooms (freeClean) or a custom area (clean_V2)."""
    if mode == CleanMode.SPOT_AREA:
        return _CleanRoomsV2(area)
    return CleanAreaV2(mode, area, cleanings)


def get_device_info() -> StaticDeviceInfo:
    """Get device info for this model."""
    return StaticDeviceInfo(
        DataType.JSON,
        Capabilities(
            device_type=DeviceType.VACUUM,
            availability=CapabilityEvent(
                AvailabilityEvent, [GetBattery(is_available_check=True)]
            ),
            battery=CapabilityEvent(BatteryEvent, [GetBattery()]),
            charge=CapabilityExecute(Charge),
            clean=CapabilityClean(
                action=CapabilityCleanAction(command=CleanV2, area=_clean_area),
                continuous=CapabilitySetEnable(
                    ContinuousCleaningEvent,
                    [GetContinuousCleaning()],
                    SetContinuousCleaning,
                ),
                count=CapabilitySet(CleanCountEvent, [GetCleanCount()], SetCleanCount),
                log=CapabilityEvent(CleanLogEvent, [GetCleanLogs()]),
                work_mode=CapabilitySetTypes(
                    event=WorkModeEvent,
                    get=[GetWorkMode()],
                    set=SetWorkMode,
                    types=(
                        WorkMode.MOP,
                        WorkMode.MOP_AFTER_VACUUM,
                        WorkMode.VACUUM,
                        WorkMode.VACUUM_AND_MOP,
                    ),
                ),
            ),
            custom=CapabilityCustomCommand(
                event=CustomCommandEvent, get=[], set=CustomCommand
            ),
            error=CapabilityEvent(ErrorEvent, [GetError()]),
            fan_speed=CapabilitySetTypes(
                event=FanSpeedEvent,
                get=[GetFanSpeed()],
                set=SetFanSpeed,
                types=(
                    FanSpeedLevel.QUIET,
                    FanSpeedLevel.NORMAL,
                    FanSpeedLevel.MAX,
                    FanSpeedLevel.MAX_PLUS,
                ),
            ),
            life_span=CapabilityLifeSpan(
                types=(
                    LifeSpan.BRUSH,
                    LifeSpan.CLEANING_SOLUTION,
                    LifeSpan.DUST_BAG,
                    LifeSpan.DUST_BUCKET,
                    LifeSpan.DUST_CONTAINER_FILTER,
                    LifeSpan.FILTER,
                    LifeSpan.HEAVY_DUTY_CLEANING_SOLUTION,
                    LifeSpan.MOP_WASHING_TRAY,
                    LifeSpan.ROUND_MOP,
                    LifeSpan.SIDE_BRUSH,
                    LifeSpan.STRAINER,
                    LifeSpan.UNIT_CARE,
                ),
                event=LifeSpanEvent,
                get=[
                    GetLifeSpan(
                        [
                            LifeSpan.BRUSH,
                            LifeSpan.CLEANING_SOLUTION,
                            LifeSpan.DUST_BAG,
                            LifeSpan.DUST_BUCKET,
                            LifeSpan.DUST_CONTAINER_FILTER,
                            LifeSpan.FILTER,
                            LifeSpan.HEAVY_DUTY_CLEANING_SOLUTION,
                            LifeSpan.MOP_WASHING_TRAY,
                            LifeSpan.ROUND_MOP,
                            LifeSpan.SIDE_BRUSH,
                            LifeSpan.STRAINER,
                            LifeSpan.UNIT_CARE,
                        ]
                    )
                ],
                reset=ResetLifeSpan,
            ),
            map=CapabilityMap(
                cached_info=CapabilityEvent(CachedMapInfoEvent, [GetCachedMapInfo()]),
                changed=CapabilityEvent(MapChangedEvent, []),
                info=CapabilityExecute(GetMapInfoV2),
                position=CapabilityEvent(PositionsEvent, [GetPos()]),
                relocation=CapabilityExecute(SetRelocationState),
                rooms=CapabilityEvent(RoomsEvent, [GetCachedMapInfo()]),
                set=CapabilityExecute(GetMapSetV2),
                trace=CapabilityEvent(MapTraceEvent, [GetMapTrace()]),
            ),
            network=CapabilityEvent(NetworkInfoEvent, [GetNetInfo()]),
            play_sound=CapabilityExecute(PlaySound),
            settings=CapabilitySettings(
                child_lock=CapabilitySetEnable(
                    ChildLockEvent, [GetChildLock()], SetChildLock
                ),
                mop_auto_wash_frequency=CapabilityNumber(
                    event=MopAutoWashFrequencyEvent,
                    get=[GetMopAutoWashFrequency()],
                    set=SetMopAutoWashFrequency,
                    min=0,
                    max=60,
                ),
                ota=CapabilitySetEnable(OtaEvent, [GetOta()], SetOta),
                sweep_mode=CapabilitySetEnable(
                    SweepModeEvent, [GetSweepMode()], SetSweepMode
                ),
                true_detect=CapabilitySetEnable(
                    TrueDetectEvent, [GetTrueDetect()], SetTrueDetect
                ),
                voice_assistant=CapabilitySetEnable(
                    VoiceAssistantStateEvent,
                    [GetVoiceAssistantState()],
                    SetVoiceAssistantState,
                ),
                volume=CapabilitySet(VolumeEvent, [GetVolume()], SetVolume),
            ),
            state=CapabilityEvent(StateEvent, [GetChargeState(), GetWorkState()]),
            station=CapabilityStation(
                action=CapabilityExecuteTypes(
                    station_action.StationAction,
                    types=(
                        StationAction.EMPTY_DUSTBIN,
                        StationAction.DRY_MOP,
                        StationAction.WASH_MOP,
                    ),
                ),
                auto_empty=CapabilitySetTypes(
                    event=AutoEmptyEvent,
                    get=[GetAutoEmpty()],
                    set=SetAutoEmpty,
                    types=(
                        auto_empty.Frequency.AUTO,
                        auto_empty.Frequency.SMART,
                    ),
                ),
                state=CapabilityEvent(StationEvent, [GetWorkState()]),
            ),
            stats=CapabilityStats(
                clean=CapabilityEvent(StatsEvent, [GetStats()]),
                report=CapabilityEvent(ReportStatsEvent, []),
                total=CapabilityEvent(TotalStatsEvent, [GetTotalStats()]),
            ),
            water=CapabilityWater(
                amount=CapabilityNumber(
                    event=water_info.WaterCustomAmountEvent,
                    get=[GetWaterInfo()],
                    set=lambda custom_amount: SetWaterInfo(custom_amount=custom_amount),
                    min=0,
                    max=50,
                ),
                mop_attached=CapabilityEvent(
                    water_info.MopAttachedEvent, [GetWaterInfo()]
                ),
            ),
        ),
    )
