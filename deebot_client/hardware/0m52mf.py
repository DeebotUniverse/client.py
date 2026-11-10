"""GOAT A2000 LiDAR PRO."""

from __future__ import annotations

from deebot_client.capabilities import (
    Capabilities,
    CapabilityClean,
    CapabilityCleanAction,
    CapabilityCustomCommand,
    CapabilityEvent,
    CapabilityExecute,
    CapabilityLifeSpan,
    CapabilitySettings,
    CapabilityStats,
    DeviceType,
)
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
from deebot_client.const import DataType
from deebot_client.events import (
    AvailabilityEvent,
    BatteryEvent,
    CustomCommandEvent,
    ErrorEvent,
    LifeSpan,
    LifeSpanEvent,
    NetworkInfoEvent,
    ReportStatsEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
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
                types=(LifeSpan.BLADE, LifeSpan.TRIMMER_BRUSH, LifeSpan.WEED_ROPE),
                event=LifeSpanEvent,
                get=[
                    GetLifeSpan(
                        [
                            LifeSpan.BLADE,
                            LifeSpan.TRIMMER_BRUSH,
                            LifeSpan.WEED_ROPE,
                        ]
                    )
                ],
                reset=ResetLifeSpan,
            ),
            network=CapabilityEvent(NetworkInfoEvent, [GetNetInfo()]),
            play_sound=CapabilityExecute(PlaySound),
            settings=CapabilitySettings(),
            state=CapabilityEvent(StateEvent, [GetChargeState(), GetCleanInfoV2()]),
            stats=CapabilityStats(
                clean=CapabilityEvent(StatsEvent, [GetStats()]),
                report=CapabilityEvent(ReportStatsEvent, []),
                total=CapabilityEvent(TotalStatsEvent, [GetTotalStats()]),
            ),
        ),
    )
