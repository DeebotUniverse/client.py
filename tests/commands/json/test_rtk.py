"""Tests for the GetRtk command."""

from __future__ import annotations

from deebot_client.commands.json import GetRtk
from deebot_client.events import RtkBaseStation, RtkEvent
from tests.commands.json import assert_command
from tests.helpers import get_request_json, get_success_body


async def test_GetRtk() -> None:
    """Parse a real GOAT A1600 RTK getRTK response."""
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "result": 0,
                "rtks": [
                    {
                        "x": -5332,
                        "y": -518,
                        "sn": "908276",
                        "state": 0,
                        "mode": 0,
                        "star": 30,
                        "version": (
                            "630ZG-B23A5-1,QD302 1.3.8,630ZG-B23A5-1,QD302 1.3.1"
                        ),
                    }
                ],
                "observations": {
                    "solStat": 0,
                    "poseType": 50,
                    "roverId": "908336",
                    "roverSvs": 35,
                    "roverSolnSvs": 30,
                    "roverSignalRate": 44,
                    "roverSignalScore": 90,
                    "roverOcclusionRate": 8,
                    "baseStnId": '"1544"',
                    "baseSolnSvs": 29,
                    "baseSignalRate": 45,
                    "baseSignalScore": 94,
                    "baseOcclusionRate": 24,
                },
            }
        )
    )
    await assert_command(
        GetRtk(),
        json,
        (
            firmware_event,
            RtkEvent(
                rover_serial_number="908336",
                rover_satellites_visible=35,
                rover_satellites_used=30,
                base_satellites_used=29,
                rover_signal_score=90,
                base_signal_score=94,
                rover_occlusion_rate=8,
                base_occlusion_rate=24,
                base_stations=[
                    RtkBaseStation(
                        serial_number="908276",
                        satellites_visible=30,
                        firmware=(
                            "630ZG-B23A5-1,QD302 1.3.8,630ZG-B23A5-1,QD302 1.3.1"
                        ),
                        state=0,
                        mode=0,
                    )
                ],
                base_station_id='"1544"',
                solution_status=0,
                pose_type=50,
            ),
        ),
    )


async def test_GetRtk_no_base_stations() -> None:
    """A response with `rtks` empty still notifies the rover-side event."""
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "result": 0,
                "rtks": [],
                "observations": {
                    "solStat": 0,
                    "poseType": 0,
                    "roverId": "908336",
                    "roverSvs": 12,
                    "roverSolnSvs": 8,
                    "roverSignalRate": 30,
                    "roverSignalScore": 50,
                    "roverOcclusionRate": 20,
                    "baseStnId": "",
                    "baseSolnSvs": 0,
                    "baseSignalRate": 0,
                    "baseSignalScore": 0,
                    "baseOcclusionRate": 0,
                },
            }
        )
    )
    await assert_command(
        GetRtk(),
        json,
        (
            firmware_event,
            RtkEvent(
                rover_serial_number="908336",
                rover_satellites_visible=12,
                rover_satellites_used=8,
                base_satellites_used=0,
                rover_signal_score=50,
                base_signal_score=0,
                rover_occlusion_rate=20,
                base_occlusion_rate=0,
                base_stations=[],
                base_station_id="",
                solution_status=0,
                pose_type=0,
            ),
        ),
    )
