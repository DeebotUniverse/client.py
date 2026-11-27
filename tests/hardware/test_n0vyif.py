from __future__ import annotations

from deebot_client.commands import StationAction
from deebot_client.hardware.n0vyif import get_device_info


def test_n0vyif_station_actions() -> None:
    capabilities = get_device_info().capabilities

    assert capabilities.station is not None
    assert capabilities.station.action.types == (
        StationAction.EMPTY_DUSTBIN,
        StationAction.WASH_MOP,
        StationAction.DRY_MOP,
    )
