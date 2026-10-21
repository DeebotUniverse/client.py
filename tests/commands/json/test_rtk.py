"""Tests for the GetRtk command."""

from __future__ import annotations

from deebot_client.commands.json import GetRtk
from deebot_client.events import RtkBaseStation, RtkEvent
from deebot_client.message import HandlingResult, HandlingState
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


async def test_GetRtk_missing_observations_returns_analyse() -> None:
    """No ``observations`` in the payload → defer to the analyse fallback.

    Guards the ``if not observations`` early return; the device firmware
    may omit the field entirely on early boot or under RTK lock loss.
    """
    json, firmware_event = get_request_json(get_success_body({"result": 0, "rtks": []}))
    await assert_command(
        GetRtk(),
        json,
        firmware_event,
        handling_result=HandlingResult(HandlingState.ANALYSE_LOGGED),
    )


async def test_GetRtk_skips_non_dict_rtks_entries() -> None:
    """A malformed ``rtks`` entry (not a dict) is skipped, not raised.

    Real captures haven't shown this yet but the firmware occasionally
    sends stray strings or nulls in list fields — we don't want the whole
    event to be lost when a single entry is off-shape.
    """
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "result": 0,
                "rtks": [
                    "not-a-dict",
                    None,
                    {
                        "sn": "908276",
                        "star": 30,
                        "state": 0,
                        "mode": 0,
                        "version": "fw",
                    },
                ],
                "observations": {
                    "solStat": 0,
                    "poseType": 0,
                    "roverId": "908336",
                    "roverSvs": 10,
                    "roverSolnSvs": 8,
                    "roverSignalScore": 40,
                    "roverOcclusionRate": 15,
                    "baseStnId": "",
                    "baseSolnSvs": 5,
                    "baseSignalScore": 30,
                    "baseOcclusionRate": 20,
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
                rover_satellites_visible=10,
                rover_satellites_used=8,
                base_satellites_used=5,
                rover_signal_score=40,
                base_signal_score=30,
                rover_occlusion_rate=15,
                base_occlusion_rate=20,
                base_stations=[
                    RtkBaseStation(
                        serial_number="908276",
                        satellites_visible=30,
                        firmware="fw",
                        state=0,
                        mode=0,
                    )
                ],
                base_station_id="",
                solution_status=0,
                pose_type=0,
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
