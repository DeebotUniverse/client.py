"""DEEBOT GOAT O800 RTK Capabilities."""

from __future__ import annotations

from deebot_client.capabilities import (
    Capabilities,
    CapabilityClean,
    CapabilityCleanAction,
    CapabilityCustomCommand,
    CapabilityEvent,
    CapabilityExecute,
    CapabilityLifeSpan,
    CapabilityMower,
    CapabilitySet,
    CapabilitySetEnable,
    CapabilitySettings,
    CapabilitySetTypes,
    CapabilityStats,
    DeviceType,
)
from deebot_client.commands.json import (
    GetBorderSwitch,
    GetCrossMapBorderWarning,
    GetCutDirection,
    GetMoveUpWarning,
    GetSafeProtect,
    SetBorderSwitch,
    SetCrossMapBorderWarning,
    SetCutDirection,
    SetMoveUpWarning,
    SetSafeProtect,
)
from deebot_client.commands.json.anim_protect import GetAnimProtect, SetAnimProtect
from deebot_client.commands.json.area_parameter import (
    GetAreaParameter,
    SetAreaParameter,
)
from deebot_client.commands.json.area_set import GetMowingAreas
from deebot_client.commands.json.auto_cut_direction import (
    GetAutoCutDirection,
    SetAutoCutDirection,
)
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.border_switch import SetBorderSwitchMode
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import (
    CleanAreaMower,
    CleanBorderMower,
    CleanMower,
    GetCleanInfoMower,
)
from deebot_client.commands.json.custom import CustomCommand
from deebot_client.commands.json.cut_efficiency import (
    GetCutEfficiency,
    SetCutEfficiency,
)
from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.geolocation import GetGeolocation, SetGeolocation
from deebot_client.commands.json.life_span import GetLifeSpan, ResetLifeSpan
from deebot_client.commands.json.network import GetNetInfo
from deebot_client.commands.json.play_sound import PlayAlarmSound
from deebot_client.commands.json.protect_state import GetProtectState
from deebot_client.commands.json.rain_delay import GetRainDelay, SetRainDelay
from deebot_client.commands.json.recognization import (
    GetRecognization,
    SetRecognization,
)
from deebot_client.commands.json.rtk import GetRtk
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.const import DataType
from deebot_client.events import (
    AiRecognitionEvent,
    AutoCutDirectionEvent,
    AvailabilityEvent,
    BatteryEvent,
    BorderSwitchEvent,
    CrossMapBorderWarningEvent,
    CustomCommandEvent,
    CutDirectionEvent,
    ErrorEvent,
    GeolocationEvent,
    LifeSpan,
    LifeSpanEvent,
    MoveUpWarningEvent,
    NetworkInfoEvent,
    ReportStatsEvent,
    SafeProtectEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
)
from deebot_client.events.mower import (
    AnimalProtectionEvent,
    AreaParametersEvent,
    BorderSwitchMode,
    BorderSwitchModeEvent,
    CutEfficiency,
    CutEfficiencyEvent,
    MowedAreaEvent,
    MowingAreasEvent,
    MowingTaskEvent,
    ProtectStateEvent,
    RainDelayEvent,
    RtkBaseStationEvent,
    RtkSignalEvent,
)
from deebot_client.models import StaticDeviceInfo


def get_device_info() -> StaticDeviceInfo:
    """Get device info for this model."""
    return StaticDeviceInfo(
        DataType.JSON,
        Capabilities(
            device_type=DeviceType.MOWER,
            availability=CapabilityEvent(
                AvailabilityEvent, [GetBattery(is_available_check=True)]
            ),
            battery=CapabilityEvent(BatteryEvent, [GetBattery()]),
            charge=CapabilityExecute(Charge),
            clean=CapabilityClean(
                action=CapabilityCleanAction(command=CleanMower, area=CleanAreaMower),
            ),
            custom=CapabilityCustomCommand(
                event=CustomCommandEvent, get=[], set=CustomCommand
            ),
            error=CapabilityEvent(ErrorEvent, [GetError()]),
            life_span=CapabilityLifeSpan(
                types=(LifeSpan.BLADE, LifeSpan.LENS_BRUSH),
                event=LifeSpanEvent,
                get=[
                    GetLifeSpan(
                        [
                            LifeSpan.BLADE,
                            LifeSpan.LENS_BRUSH,
                        ]
                    )
                ],
                reset=ResetLifeSpan,
            ),
            mower=CapabilityMower(
                areas=CapabilityEvent(MowingAreasEvent, [GetMowingAreas()]),
                border=CapabilityExecute(CleanBorderMower),
                area_parameters=CapabilitySet(
                    AreaParametersEvent, [GetAreaParameter()], SetAreaParameter
                ),
                mowed_area=CapabilityEvent(MowedAreaEvent, [GetStats()]),
                protect_state=CapabilityEvent(ProtectStateEvent, [GetProtectState()]),
                rtk_base_station=CapabilityEvent(RtkBaseStationEvent, [GetRtk()]),
                rtk_signal=CapabilityEvent(RtkSignalEvent, [GetRtk()]),
                task=CapabilityEvent(MowingTaskEvent, [GetCleanInfoMower()]),
            ),
            network=CapabilityEvent(NetworkInfoEvent, [GetNetInfo()]),
            play_sound=CapabilityExecute(PlayAlarmSound),
            settings=CapabilitySettings(
                ai_recognition=CapabilitySetEnable(
                    AiRecognitionEvent, [GetRecognization()], SetRecognization
                ),
                animal_protection=CapabilitySet(
                    AnimalProtectionEvent, [GetAnimProtect()], SetAnimProtect
                ),
                auto_cut_direction=CapabilitySetEnable(
                    AutoCutDirectionEvent, [GetAutoCutDirection()], SetAutoCutDirection
                ),
                border_switch=CapabilitySetEnable(
                    BorderSwitchEvent, [GetBorderSwitch()], SetBorderSwitch
                ),
                border_switch_mode=CapabilitySetTypes(
                    event=BorderSwitchModeEvent,
                    get=[GetBorderSwitch()],
                    set=SetBorderSwitchMode,
                    types=(
                        BorderSwitchMode.ALONG_BORDER,
                        BorderSwitchMode.EDGE_MOWING,
                        BorderSwitchMode.CROSS_BOUNDARY,
                    ),
                ),
                cut_direction=CapabilitySet(
                    CutDirectionEvent, [GetCutDirection()], SetCutDirection
                ),
                cut_efficiency=CapabilitySetTypes(
                    event=CutEfficiencyEvent,
                    get=[GetCutEfficiency()],
                    set=SetCutEfficiency,
                    types=(CutEfficiency.EFFICIENT, CutEfficiency.FINE),
                ),
                moveup_warning=CapabilitySetEnable(
                    MoveUpWarningEvent, [GetMoveUpWarning()], SetMoveUpWarning
                ),
                cross_map_border_warning=CapabilitySetEnable(
                    CrossMapBorderWarningEvent,
                    [GetCrossMapBorderWarning()],
                    SetCrossMapBorderWarning,
                ),
                geolocation=CapabilitySetEnable(
                    GeolocationEvent, [GetGeolocation()], SetGeolocation
                ),
                rain_delay=CapabilitySet(
                    RainDelayEvent, [GetRainDelay()], SetRainDelay
                ),
                safe_protect=CapabilitySetEnable(
                    SafeProtectEvent, [GetSafeProtect()], SetSafeProtect
                ),
            ),
            state=CapabilityEvent(StateEvent, [GetChargeState(), GetCleanInfoMower()]),
            stats=CapabilityStats(
                clean=CapabilityEvent(StatsEvent, [GetStats()]),
                report=CapabilityEvent(ReportStatsEvent, []),
                total=CapabilityEvent(TotalStatsEvent, [GetTotalStats()]),
            ),
        ),
    )
