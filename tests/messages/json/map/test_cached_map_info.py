from __future__ import annotations

from deebot_client.events import FirmwareEvent
from deebot_client.events.map import (
    CachedMapInfoEvent,
    Map,
    PredefinedMapNames,
)
from deebot_client.messages.json.map.cached_map_info import OnCachedMapInfo
from tests.messages import assert_message


def test_onCachedMapInfo() -> None:
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
            },
        },
    }

    result = assert_message(
        OnCachedMapInfo,
        data,
        (
            FirmwareEvent("1.34.0"),
            CachedMapInfoEvent(
                {
                    Map(
                        id="1048154397",
                        name=PredefinedMapNames.NOT_FINISHED,
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
        ),
    )
    assert result.args == {"map_id": "1132127808"}
