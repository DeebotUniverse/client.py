"""Yeedi S20 / DEEBOT X11 OmniCyclone Capabilities."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from deebot_client.capabilities import CapabilityExecute, CapabilityLifeSpan
from deebot_client.commands.json.life_span import GetLifeSpan, ResetLifeSpan
from deebot_client.commands.json.map import GetMapSetV2NoRoomSubsets
from deebot_client.events import LifeSpan, LifeSpanEvent
from deebot_client.hardware import n0vyif

if TYPE_CHECKING:
    from deebot_client.models import StaticDeviceInfo


def get_device_info() -> StaticDeviceInfo:
    """Get device info for this model."""
    info = n0vyif.get_device_info()
    capabilities = info.capabilities
    map_capability = capabilities.map
    if map_capability is None:
        return info

    return replace(
        info,
        capabilities=replace(
            capabilities,
            clean=replace(capabilities.clean, log=None),
            life_span=CapabilityLifeSpan(
                types=(
                    LifeSpan.BRUSH,
                    LifeSpan.FILTER,
                    LifeSpan.SIDE_BRUSH,
                    LifeSpan.CLEANING_SOLUTION,
                    LifeSpan.SEWAGE_BOX,
                ),
                event=LifeSpanEvent,
                get=[
                    GetLifeSpan(
                        [
                            LifeSpan.BRUSH,
                            LifeSpan.FILTER,
                            LifeSpan.SIDE_BRUSH,
                            LifeSpan.CLEANING_SOLUTION,
                            LifeSpan.SEWAGE_BOX,
                        ]
                    )
                ],
                reset=ResetLifeSpan,
            ),
            map=replace(
                map_capability,
                set=CapabilityExecute(GetMapSetV2NoRoomSubsets),
            ),
        ),
    )
