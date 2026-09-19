"""DEEBOT X12 OmniCyclone capabilities."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from deebot_client.commands.json.clean import CleanAreaV2
from deebot_client.hardware.fd60kt import get_device_info as get_t50_device_info
from deebot_client.models import CleanMode, StaticDeviceInfo

if TYPE_CHECKING:
    from deebot_client.command import Command


def _get_free_clean_area(
    _mode: CleanMode, area: list[int | float], cleanings: int = 1
) -> Command:
    """Clean selected X12 rooms using the V2 freeClean command shape."""
    return CleanAreaV2(CleanMode.FREE_CLEAN, area, cleanings)


def get_device_info() -> StaticDeviceInfo:
    """Get device info for the DEEBOT X12 OmniCyclone."""
    device_info = get_t50_device_info()
    capabilities = device_info.capabilities
    clean = capabilities.clean

    return replace(
        device_info,
        capabilities=replace(
            capabilities,
            clean=replace(
                clean,
                action=replace(clean.action, area=_get_free_clean_area),
            ),
        ),
    )
