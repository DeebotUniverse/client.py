"""Tests regarding protect state and RTK commands."""

from __future__ import annotations

from deebot_client.commands.json import GetProtectState, GetRtk
from deebot_client.events.mower import (
    ProtectStateEvent,
    RtkBaseStationEvent,
    RtkFixType,
    RtkSignalEvent,
)
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.messages.json import OnRtk
from tests.helpers import get_message_json, get_request_json, get_success_body
from tests.messages.json import assert_message

from . import assert_command

_RTK_STATION = {
    "x": 5421,
    "y": 3431,
    "sn": "123456",
    "state": 0,
    "mode": 0,
    "star": 31,
    "version": "630ZZ-B26A3-1,QD302 1.4.5",
}


async def test_GetProtectState() -> None:
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "isAnimProtect": 0,
                "isRainProtect": 1,
                "isRainDelay": 0,
                "isEStop": 0,
                "isLocked": 0,
                "isPinCode": 0,
                "isPrepareDataSuccess": 1,
            }
        )
    )
    await assert_command(
        GetProtectState(),
        json,
        (
            firmware_event,
            ProtectStateEvent(
                animal_protection=False,
                rain_protection=True,
                rain_delay=False,
                emergency_stop=False,
                locked=False,
            ),
        ),
    )


async def test_GetRtk() -> None:
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "result": 0,
                "rtks": [_RTK_STATION],
                "observations": {
                    "solStat": 0,
                    "poseType": 50,
                    "roverId": "123456",
                    "roverSvs": 44,
                    "roverSolnSvs": 31,
                    "roverSignalRate": 42,
                    "roverSignalScore": 78,
                    "roverOcclusionRate": 5,
                    "baseStnId": '"4014"',
                    "baseSolnSvs": 33,
                    "baseSignalRate": 40,
                    "baseSignalScore": 74,
                    "baseOcclusionRate": 17,
                },
            }
        )
    )
    await assert_command(
        GetRtk(),
        json,
        (
            firmware_event,
            RtkBaseStationEvent(state=0, satellites=31, position=(5421.0, 3431.0)),
            RtkSignalEvent(
                fix_type=RtkFixType.FIXED,
                rover_satellites=31,
                rover_signal_score=78,
                rover_occlusion_rate=5,
                base_satellites=33,
                base_signal_score=74,
                base_occlusion_rate=17,
            ),
        ),
    )


def test_onRtk() -> None:
    data, firmware_event = get_message_json(
        {
            "data": {"result": 0, "rtks": [{**_RTK_STATION, "state": 1, "mode": 112}]},
            "code": 0,
            "msg": "",
        }
    )
    assert_message(
        OnRtk,
        data,
        (
            firmware_event,
            RtkBaseStationEvent(state=1, satellites=31, position=(5421.0, 3431.0)),
        ),
    )


def test_onRtk_no_position() -> None:
    data, firmware_event = get_message_json(
        {"data": {"result": 0, "rtks": [{**_RTK_STATION, "x": 0, "y": 0, "star": 0}]}}
    )
    assert_message(
        OnRtk,
        data,
        (firmware_event, RtkBaseStationEvent(state=0, satellites=0, position=None)),
    )


def test_onRtk_analyse() -> None:
    data, firmware_event = get_message_json({"data": {"result": 0, "rtks": []}})
    result = assert_message(
        OnRtk, data, firmware_event, expected_state=HandlingState.ANALYSE_LOGGED
    )
    assert result == HandlingResult(HandlingState.ANALYSE_LOGGED)
