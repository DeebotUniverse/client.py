"""DEEBOT X12 OmniCyclone capabilities."""

from __future__ import annotations

from dataclasses import replace

from deebot_client.commands.json.clean import CleanAreaV2
from deebot_client.hardware.fd60kt import get_device_info as get_t50_device_info
from deebot_client.models import CleanMode, StaticDeviceInfo


class _CleanAreaFreeCleanV2(CleanAreaV2):
    """Serialize X12 rooms as count,room pairs while preserving coordinates."""

    def __init__(
        self, mode: CleanMode, area: list[int | float], cleanings: int = 1
    ) -> None:
        if mode in (CleanMode.SPOT_AREA, CleanMode.FREE_CLEAN):
            super().__init__(CleanMode.FREE_CLEAN, area, cleanings)
            self._additional_content["value"] = ";".join(
                f"{cleanings},{int(room)}" for room in area
            )
        else:
            super().__init__(mode, area, cleanings)


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
                action=replace(clean.action, area=_CleanAreaFreeCleanV2),
            ),
        ),
    )
