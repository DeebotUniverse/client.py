"""Network commands."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from deebot_client.events import NetworkInfoEvent
from deebot_client.message import HandlingResult

from .common import RobotDetailGetCommand


class GetNetInfo(RobotDetailGetCommand):
    """Get network info from the robot-detail surface."""

    NAME = 'getNetInfo'
    FIELDS = ('deviceInfo',)

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus,
        data: dict[str, Any],
    ) -> HandlingResult:
        device_info = data.get('deviceInfo', {})
        if not isinstance(device_info, Mapping):
            device_info = {}
        event_bus.notify(
            NetworkInfoEvent(
                ip=str(device_info.get('ip', '')),
                ssid=str(device_info.get('ssid', '')),
                rssi=_coerce_rssi(device_info.get('rssi')),
                mac=str(device_info.get('mac', '')),
            )
        )
        return HandlingResult.success()


def _coerce_rssi(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
