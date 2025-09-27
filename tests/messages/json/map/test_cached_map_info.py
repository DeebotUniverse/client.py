from __future__ import annotations

from typing import Any

import pytest

from deebot_client.events import FirmwareEvent
from deebot_client.events.map import (
    CachedMapInfoEvent,
    Map,
)
from deebot_client.message import HandlingState
from deebot_client.messages.json.map.cached_map_info import OnCachedMapInfo
from tests.messages import assert_message


@pytest.mark.parametrize(
    ("info", "expected_event", "expected_args"),
    [
        (
            [
                {
                    "mid": "1048154397",
                    "backupId": "0",
                    "status": 1,
                    "index": 3,
                    "using": 0,
                    "built": 0,
                    "name": "",
                    "isFastBuilding": 1,
                },
                {
                    "mid": "1132127808",
                    "backupId": "1881930203",
                    "status": 0,
                    "index": 0,
                    "using": 1,
                    "built": 1,
                    "name": "Erdgeschoss",
                    "isFastBuilding": 1,
                },
                {
                    "mid": "0",
                    "backupId": "",
                    "status": 1,
                    "index": 1,
                    "using": 0,
                    "built": 0,
                    "name": "",
                    "isFastBuilding": 0,
                },
                {
                    "mid": "0",
                    "backupId": "",
                    "status": 1,
                    "index": 2,
                    "using": 0,
                    "built": 0,
                    "name": "",
                    "isFastBuilding": 0,
                },
            ],
            CachedMapInfoEvent(
                {
                    Map(
                        id="1048154397",
                        name="",
                        using=False,
                        built=False,
                    ),
                    Map(
                        id="1132127808",
                        name="Erdgeschoss",
                        using=True,
                        built=True,
                    ),
                }
            ),
            {"map_id": "1132127808"},
        ),
        (
            [
                {
                    "mid": "1048154397",
                    "backupId": "0",
                    "status": 1,
                    "index": 3,
                    "using": 1,
                    "built": 0,
                    "name": "",
                    "isFastBuilding": 1,
                },
                {
                    "mid": "0",
                    "backupId": "0",
                    "status": 0,
                    "index": 0,
                    "using": 0,
                    "built": 0,
                    "name": "",
                    "isFastBuilding": 1,
                },
                {
                    "mid": "0",
                    "backupId": "",
                    "status": 1,
                    "index": 1,
                    "using": 0,
                    "built": 0,
                    "name": "",
                    "isFastBuilding": 0,
                },
                {
                    "mid": "0",
                    "backupId": "",
                    "status": 1,
                    "index": 2,
                    "using": 0,
                    "built": 0,
                    "name": "",
                    "isFastBuilding": 0,
                },
            ],
            CachedMapInfoEvent(
                {
                    Map(
                        id="1048154397",
                        name="",
                        using=True,
                        built=False,
                    ),
                }
            ),
            {"map_id": "1048154397"},
        ),
    ],
)
def test_onCachedMapInfo(
    info: list[dict[str, Any]],
    expected_event: CachedMapInfoEvent,
    expected_args: dict[str, Any],
) -> None:
    """Test onCachedMapInfo message."""
    data = {
        "header": {
            "pri": 1,
            "tzm": 60,
            "ts": "1758910286337",
            "ver": "0.0.1",
            "fwVer": "1.34.0",
            "hwVer": "0.1.1",
            "wkVer": "0.1.54",
        },
        "body": {
            "code": 0,
            "msg": "ok",
            "data": {"enable": 1, "info": info},
        },
    }

    result = assert_message(
        OnCachedMapInfo,
        data,
        (
            FirmwareEvent("1.34.0"),
            expected_event,
        ),
    )
    assert result.args == expected_args


@pytest.mark.parametrize(
    ("first_map_id", "expected_events"),
    [
        (
            "1048154397",
            [
                CachedMapInfoEvent(
                    {Map(id="1048154397", name="", using=False, built=False)}
                )
            ],
        ),
        ("0", []),
    ],
)
def test_onCachedMapInfo_no_using_map(
    first_map_id: str, expected_events: list[CachedMapInfoEvent]
) -> None:
    """Test onCachedMapInfo message."""
    data = {
        "header": {
            "pri": 1,
            "tzm": 60,
            "ts": "1758910286337",
            "ver": "0.0.1",
            "fwVer": "1.34.0",
            "hwVer": "0.1.1",
            "wkVer": "0.1.54",
        },
        "body": {
            "code": 0,
            "msg": "ok",
            "data": {
                "enable": 1,
                "info": [
                    {
                        "mid": first_map_id,
                        "backupId": "0",
                        "status": 1,
                        "index": 3,
                        "using": 0,
                        "built": 0,
                        "name": "",
                        "isFastBuilding": 1,
                    },
                    {
                        "mid": "0",
                        "backupId": "0",
                        "status": 0,
                        "index": 0,
                        "using": 1,
                        "built": 0,
                        "name": "",
                        "isFastBuilding": 1,
                    },
                    {
                        "mid": "0",
                        "backupId": "",
                        "status": 1,
                        "index": 1,
                        "using": 0,
                        "built": 0,
                        "name": "",
                        "isFastBuilding": 0,
                    },
                    {
                        "mid": "0",
                        "backupId": "",
                        "status": 1,
                        "index": 2,
                        "using": 0,
                        "built": 0,
                        "name": "",
                        "isFastBuilding": 0,
                    },
                ],
            },
        },
    }

    result = assert_message(
        OnCachedMapInfo,
        data,
        (
            FirmwareEvent("1.34.0"),
            *expected_events,
        ),
        expected_state=HandlingState.ANALYSE_LOGGED,
    )
    assert result.args is None
