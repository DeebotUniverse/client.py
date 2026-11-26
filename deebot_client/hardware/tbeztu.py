"""DEEBOT X12 PRO OMNI capabilities."""

from __future__ import annotations

from dataclasses import replace

from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import CleanAreaV2
from deebot_client.commands.json.work_state import GetWorkState
from deebot_client.hardware.fd60kt import get_device_info as get_t50_device_info
from deebot_client.models import CleanAction, CleanMode, StaticDeviceInfo


class _CleanAreaFreeCleanV2(CleanAreaV2):
    """Room cleaning for the X12 PRO OMNI.

    The bot rejects clean_V2 with spotArea (20011 "unknown type"). Rooms have
    to be sent as freeClean with one "1,<room id>" pair per room, joined by
    ";". The leading 1 is the area type (room), not the number of passes; the
    passes come from the clean count setting. Custom areas are left as is.
    """

    def __init__(
        self, mode: CleanMode, area: list[int | float], cleanings: int = 1
    ) -> None:
        if mode in (CleanMode.SPOT_AREA, CleanMode.FREE_CLEAN):
            super().__init__(CleanMode.FREE_CLEAN, area, cleanings)
            self._additional_content["value"] = ";".join(
                f"1,{int(room)}" for room in area
            )
            self._args = self._get_args(CleanAction.START)
        else:
            super().__init__(mode, area, cleanings)


def get_device_info() -> StaticDeviceInfo:
    """Get device info for the DEEBOT X12 PRO OMNI."""
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
            # While cleaning a room (freeClean) the state was reported as IDLE.
            # getCleanInfo_V2 doesn't seem to follow freeClean jobs, while the
            # work state reports them as cleaning, so query that instead.
            state=replace(capabilities.state, get=[GetChargeState(), GetWorkState()]),
        ),
    )
