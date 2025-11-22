from __future__ import annotations

from deebot_client.commands.json import GetNetInfo, GetNetInfoLegacy
from deebot_client.events import NetworkInfoEvent
from tests.commands.json import assert_command
from tests.helpers import (
    get_request_json,
    get_success_body,
)


async def test_GetNetInfo() -> None:
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "ip": "192.168.1.100",
                "ssid": "WLAN",
                "rssi": "-61",
                "wkVer": "0.1.2",
                "mac": "AA:BB:CC:DD:EE:FF",
            }
        )
    )
    await assert_command(
        GetNetInfo(),
        json,
        (
            firmware_event,
            NetworkInfoEvent(
                ip="192.168.1.100", ssid="WLAN", rssi=-61, mac="AA:BB:CC:DD:EE:FF"
            ),
        ),
    )


async def test_GetNetInfoRSSIdot() -> None:
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "ip": "192.168.1.100",
                "ssid": "WLAN",
                "rssi": "42.",
                "wkVer": "0.1.2",
                "mac": "AA:BB:CC:DD:EE:FF",
            }
        )
    )
    await assert_command(
        GetNetInfo(),
        json,
        (
            firmware_event,
            NetworkInfoEvent(
                ip="192.168.1.100", ssid="WLAN", rssi=42, mac="AA:BB:CC:DD:EE:FF"
            ),
        ),
    )


async def test_GetNetInfoLegacy() -> None:
    json = {
        "ret": "ok",
        "resp": {
            "ret": "ok",
            "s": "WLAN",
            "p": "",
            "wi": "192.168.1.100",
            "wm": "AA:BB:CC:DD:EE:FF",
            "st": "-61",
        },
        "id": "qvHH",
        "payloadType": "j",
    }
    await assert_command(
        GetNetInfoLegacy(),
        json,
        NetworkInfoEvent(
            ip="192.168.1.100", ssid="WLAN", rssi=-61, mac="AA:BB:CC:DD:EE:FF"
        ),
    )
