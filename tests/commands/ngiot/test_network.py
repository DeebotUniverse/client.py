from __future__ import annotations

from typing import cast
from unittest.mock import Mock

from deebot_client.commands.ngiot.network import GetNetInfo
from deebot_client.event_bus import EventBus
from deebot_client.events import NetworkInfoEvent
from deebot_client.message import HandlingState


def test_get_network_info_notifies_event() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetNetInfo.handle(
        cast("EventBus", event_bus),
        {
            "body": {
                "data": {
                    "deviceInfo": {
                        "ip": "192.168.1.50",
                        "ssid": "test-wifi",
                        "rssi": "-56",
                        "mac": "aa:bb:cc:dd:ee:ff",
                    }
                }
            }
        },
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(
        NetworkInfoEvent(
            ip="192.168.1.50",
            ssid="test-wifi",
            rssi=-56,
            mac="aa:bb:cc:dd:ee:ff",
        )
    )


def test_get_network_info_defaults_invalid_payload() -> None:
    event_bus = Mock(spec_set=EventBus)

    result = GetNetInfo.handle(
        cast("EventBus", event_bus),
        {"body": {"data": {"deviceInfo": "not-a-dict"}}},
    )

    assert result.state == HandlingState.SUCCESS
    event_bus.notify.assert_called_once_with(
        NetworkInfoEvent(ip="", ssid="", rssi=0, mac="")
    )
