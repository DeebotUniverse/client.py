"""Deebot DEEBOT T80 China capabilities."""

from __future__ import annotations

from dataclasses import dataclass, replace
from importlib import import_module
from typing import TYPE_CHECKING

from deebot_client.capabilities import (
    CapabilityEvent,
    CapabilitySettings,
    CapabilitySetTypes,
    CapabilityStation,
)
from deebot_client.commands import StationAction
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import GetCleanInfoV2
from deebot_client.commands.json.life_span import GetLifeSpan
from deebot_client.commands.json.xwk78e import (
    ChargeT80,
    CleanAreaV2FreeClean,
    GetAutoEmptyT80,
    GetCleanPreferenceT80,
    GetTrueDetectT80,
    GetWashInfoT80,
    GetWorkStateT80,
    SetAutoEmptyV2,
    SetCleanPreferenceT80,
    SetTrueDetectLevelT80,
    SetTrueDetectV2,
    SetWashInfoT80,
    StationActionT80,
)
from deebot_client.events import LifeSpan, LifeSpanEvent, StateEvent
from deebot_client.events.xwk78e import (
    AutoEmptyEventT80,
    TrueDetectLevel,
    TrueDetectLevelEvent,
    WashMode,
    WashModeEvent,
)

if TYPE_CHECKING:
    from deebot_client.models import StaticDeviceInfo


_base_get_device_info = import_module("deebot_client.hardware.9eamof").get_device_info


@dataclass(frozen=True, kw_only=True)
class CapabilityStationT80(CapabilityStation):
    """T80 station capabilities with wash-mode settings."""

    wash_mode: CapabilitySetTypes[WashModeEvent, [WashMode | str], WashMode]


@dataclass(frozen=True, kw_only=True)
class CapabilitySettingsT80(CapabilitySettings):
    """T80 settings with obstacle sensitivity selection."""

    true_detect_level: CapabilitySetTypes[
        TrueDetectLevelEvent, [TrueDetectLevel | str], TrueDetectLevel
    ] | None = None


def get_device_info() -> StaticDeviceInfo:
    """Get China T80 capabilities without changing shared profiles."""
    info = _base_get_device_info()
    capabilities = info.capabilities

    charge = replace(capabilities.charge, execute=ChargeT80)

    clean = replace(
        capabilities.clean,
        action=replace(
            capabilities.clean.action,
            area=CleanAreaV2FreeClean,
        ),
        preference=replace(
            capabilities.clean.preference,
            get=[GetCleanPreferenceT80()],
            set=SetCleanPreferenceT80,
        ),
    )

    life_span_types = (
        LifeSpan.BRUSH,
        LifeSpan.FILTER,
        LifeSpan.SIDE_BRUSH,
        LifeSpan.UNIT_CARE,
        LifeSpan.CLEANING_SOLUTION,
        LifeSpan.SEWAGE_BOX,
        LifeSpan.DUST_BAG,
        LifeSpan.ROUND_MOP,
        LifeSpan.WATER_SINK,
    )
    life_span = replace(
        capabilities.life_span,
        types=life_span_types,
        event=LifeSpanEvent,
        get=[GetLifeSpan(list(life_span_types))],
    )

    base_settings = capabilities.settings
    settings = CapabilitySettingsT80(
        advanced_mode=base_settings.advanced_mode,
        carpet_auto_fan_boost=base_settings.carpet_auto_fan_boost,
        efficiency_mode=base_settings.efficiency_mode,
        border_spin=base_settings.border_spin,
        border_switch=base_settings.border_switch,
        child_lock=base_settings.child_lock,
        cut_direction=base_settings.cut_direction,
        mop_auto_wash_frequency=base_settings.mop_auto_wash_frequency,
        moveup_warning=base_settings.moveup_warning,
        cross_map_border_warning=base_settings.cross_map_border_warning,
        safe_protect=base_settings.safe_protect,
        ota=base_settings.ota,
        sweep_mode=base_settings.sweep_mode,
        true_detect=replace(
            base_settings.true_detect,
            get=[GetTrueDetectT80()],
            set=SetTrueDetectV2,
        ),
        true_detect_level=CapabilitySetTypes(
            event=TrueDetectLevelEvent,
            get=[GetTrueDetectT80()],
            set=SetTrueDetectLevelT80,
            types=tuple(TrueDetectLevel),
        ),
        voice_assistant=base_settings.voice_assistant,
        volume=base_settings.volume,
    )

    state = CapabilityEvent(
        StateEvent,
        [GetChargeState(), GetCleanInfoV2(), GetWorkStateT80()],
    )

    station = CapabilityStationT80(
        action=replace(
            capabilities.station.action,
            execute=StationActionT80,
            types=(
                StationAction.EMPTY_DUSTBIN,
                StationAction.DRY_MOP,
                StationAction.CLEAN_BASE,
                StationAction.WASH_MOP,
            ),
        ),
        auto_empty=replace(
            capabilities.station.auto_empty,
            event=AutoEmptyEventT80,
            get=[GetAutoEmptyT80()],
            set=SetAutoEmptyV2,
        ),
        state=capabilities.station.state,
        wash_mode=CapabilitySetTypes(
            event=WashModeEvent,
            get=[GetWashInfoT80()],
            set=SetWashInfoT80,
            types=tuple(WashMode),
        ),
    )

    return replace(
        info,
        capabilities=replace(
            capabilities,
            charge=charge,
            clean=clean,
            life_span=life_span,
            settings=settings,
            state=state,
            station=station,
        ),
    )
