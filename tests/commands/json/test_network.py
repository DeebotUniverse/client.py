from deebot_client.commands.json import GetNetInfo
from deebot_client.events import NetworkInfoEvent
from tests.commands.json import assert_command
from tests.helpers import (
    get_request_json,
    get_success_body,
)


async def test_GetFanSpeed() -> None:
    json = get_request_json(
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
        NetworkInfoEvent(
            ip="192.168.1.100", ssid="WLAN", rssi=-61, mac="AA:BB:CC:DD:EE:FF"
        ),
    )
