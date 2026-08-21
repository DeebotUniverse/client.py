"""DEEBOT GOAT O1200 LiDAR (2i0fns) Capabilities."""

from __future__ import annotations

from deebot_client.capabilities import (
    Capabilities,
    CapabilityClean,
    CapabilityCleanAction,
    CapabilityCustomCommand,
    CapabilityEvent,
    CapabilityExecute,
    CapabilityLifeSpan,
    CapabilitySet,
    CapabilitySetEnable,
    CapabilitySettings,
    CapabilityStats,
    DeviceType,
)
from deebot_client.commands.json import (
    GetAnimalProtection,
    GetBorderSwitch,
    GetChildLock,
    GetCrossMapBorderWarning,
    GetCutDirection,
    GetHumanoidAi,
    GetMoveUpWarning,
    GetNarrowAdapt,
    GetRecognization,
    GetSafeProtect,
    SetAnimalProtection,
    SetBorderSwitch,
    SetChildLock,
    SetCrossMapBorderWarning,
    SetCutDirection,
    SetHumanoidAi,
    SetMoveUpWarning,
    SetNarrowAdapt,
    SetRainDelay,
    SetRecognization,
    SetSafeProtect,
)
from deebot_client.commands.json.advanced_mode import GetAdvancedMode, SetAdvancedMode
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import CleanV2, GetCleanInfoV2
from deebot_client.commands.json.custom import CustomCommand
from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.life_span import GetLifeSpan, ResetLifeSpan
from deebot_client.commands.json.network import GetNetInfo
from deebot_client.commands.json.play_sound import PlaySound
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.commands.json.true_detect import GetTrueDetect, SetTrueDetect
from deebot_client.commands.json.volume import GetVolume, SetFallVolume, SetVolume
from deebot_client.const import DataType
from deebot_client.events import (
    AdvancedModeEvent,
    AiRecognitionEvent,
    AnimalProtectionEvent,
    AvailabilityEvent,
    BatteryEvent,
    BorderSwitchEvent,
    ChildLockEvent,
    CrossMapBorderWarningEvent,
    CustomCommandEvent,
    CutDirectionEvent,
    ErrorEvent,
    FallVolumeEvent,
    HumanoidAiEvent,
    LifeSpan,
    LifeSpanEvent,
    MoveUpWarningEvent,
    NarrowAdaptEvent,
    NetworkInfoEvent,
    ProtectStateEvent,
    RainDelayEvent,
    ReportStatsEvent,
    SafeProtectEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
    TrueDetectEvent,
    VolumeEvent,
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
                action=CapabilityCleanAction(command=CleanV2),
            ),
            custom=CapabilityCustomCommand(
                event=CustomCommandEvent, get=[], set=CustomCommand
            ),
            error=CapabilityEvent(ErrorEvent, [GetError()]),
            life_span=CapabilityLifeSpan(
                types=(
                    LifeSpan.BLADE,
                    LifeSpan.LENS_BRUSH,
                    LifeSpan.WEED_ROPE,
                    LifeSpan.TRIMMER_BRUSH,
                ),
                event=LifeSpanEvent,
                get=[
                    GetLifeSpan(
                        [
                            LifeSpan.BLADE,
                            LifeSpan.LENS_BRUSH,
                            LifeSpan.WEED_ROPE,
                            LifeSpan.TRIMMER_BRUSH,
                        ]
                    )
                ],
                reset=ResetLifeSpan,
            ),
            network=CapabilityEvent(NetworkInfoEvent, [GetNetInfo()]),
            play_sound=CapabilityExecute(PlaySound),
            protect_state=CapabilityEvent(ProtectStateEvent, []),
            settings=CapabilitySettings(
                ai_recognition=CapabilitySetEnable(
                    AiRecognitionEvent, [GetRecognization()], SetRecognization
                ),
                animal_protection=CapabilitySet(
                    AnimalProtectionEvent,
                    [GetAnimalProtection()],
                    SetAnimalProtection,
                ),
                advanced_mode=CapabilitySetEnable(
                    AdvancedModeEvent, [GetAdvancedMode()], SetAdvancedMode
                ),
                border_switch=CapabilitySetEnable(
                    BorderSwitchEvent, [GetBorderSwitch()], SetBorderSwitch
                ),
                cut_direction=CapabilitySet(
                    CutDirectionEvent, [GetCutDirection()], SetCutDirection
                ),
                child_lock=CapabilitySetEnable(
                    ChildLockEvent, [GetChildLock()], SetChildLock
                ),
                moveup_warning=CapabilitySetEnable(
                    MoveUpWarningEvent, [GetMoveUpWarning()], SetMoveUpWarning
                ),
                humanoid_ai=CapabilitySetEnable(
                    HumanoidAiEvent, [GetHumanoidAi()], SetHumanoidAi
                ),
                narrow_adapt=CapabilitySetEnable(
                    NarrowAdaptEvent, [GetNarrowAdapt()], SetNarrowAdapt
                ),
                rain_delay=CapabilitySet(RainDelayEvent, [], SetRainDelay),
                cross_map_border_warning=CapabilitySetEnable(
                    CrossMapBorderWarningEvent,
                    [GetCrossMapBorderWarning()],
                    SetCrossMapBorderWarning,
                ),
                safe_protect=CapabilitySetEnable(
                    SafeProtectEvent, [GetSafeProtect()], SetSafeProtect
                ),
                true_detect=CapabilitySetEnable(
                    TrueDetectEvent, [GetTrueDetect()], SetTrueDetect
                ),
                volume=CapabilitySet(
                    VolumeEvent,
                    [GetVolume()],
                    lambda volume: SetVolume(volume, channel="sys", total=10),
                ),
                fall_volume=CapabilitySet(
                    FallVolumeEvent, [GetVolume()], SetFallVolume
                ),
            ),
            state=CapabilityEvent(StateEvent, [GetChargeState(), GetCleanInfoV2()]),
            stats=CapabilityStats(
                clean=CapabilityEvent(StatsEvent, [GetStats()]),
                report=CapabilityEvent(ReportStatsEvent, []),
                total=CapabilityEvent(TotalStatsEvent, [GetTotalStats()]),
            ),
        ),
    )
