"""Network info event module."""

from __future__ import annotations

from dataclasses import dataclass

from .base import Event


@dataclass(frozen=True)
class NetworkInfoEvent(Event):
    """Network info event representation."""

    ip: str
    ssid: str
    rssi: int
    mac: str
