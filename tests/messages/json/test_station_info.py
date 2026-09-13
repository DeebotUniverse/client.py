from __future__ import annotations

import pytest

from deebot_client.events import FirmwareEvent
from deebot_client.events.station import StationInfoEvent
from deebot_client.messages.json.station_info import OnStationInfo
from tests.messages.json import assert_message


@pytest.mark.benchmark
def test_onStationInfo() -> None:
    data = {
        "header": {
            "pri": 1,
            "tzm": 60,
            "ts": "1734719921057",
            "ver": "0.0.1",
            "fwVer": "1.8.2",
            "hwVer": "0.1.1",
            "wkVer": "0.1.54",
        },
        "body": {
            "data": {
                "state": 1,
                "name": "OMNI Station",
                "model": "OMNI",
                "sn": "000000000000000000000",
                "wkVer": "0.4.3",
            },
            "code": 0,
            "msg": "ok",
        },
    }

    assert_message(
        OnStationInfo,
        data,
        (
            FirmwareEvent("1.8.2"),
            StationInfoEvent(name="OMNI Station", model="OMNI", firmware="0.4.3"),
        ),
        device_class="55uoqe",
    )


@pytest.mark.benchmark
def test_onStationInfo_missing_fields() -> None:
    """Missing fields are treated as empty, not an error."""
    data = {
        "header": {
            "pri": 1,
            "tzm": 60,
            "ts": "1734719921057",
            "ver": "0.0.1",
            "fwVer": "1.8.2",
            "hwVer": "0.1.1",
            "wkVer": "0.1.54",
        },
        "body": {"data": {"state": 1}, "code": 0, "msg": "ok"},
    }

    assert_message(
        OnStationInfo,
        data,
        (FirmwareEvent("1.8.2"), StationInfoEvent(name="", model="", firmware="")),
        device_class="55uoqe",
    )


@pytest.mark.benchmark
def test_onStationInfo_null_fields() -> None:
    """Explicit nulls/wrong types are treated as empty, like missing fields."""
    data = {
        "header": {
            "pri": 1,
            "tzm": 60,
            "ts": "1734719921057",
            "ver": "0.0.1",
            "fwVer": "1.8.2",
            "hwVer": "0.1.1",
            "wkVer": "0.1.54",
        },
        "body": {
            "data": {"state": 1, "name": None, "model": {"a": 1}, "wkVer": [1]},
            "code": 0,
            "msg": "ok",
        },
    }

    assert_message(
        OnStationInfo,
        data,
        (FirmwareEvent("1.8.2"), StationInfoEvent(name="", model="", firmware="")),
        device_class="55uoqe",
    )
