"""Geolocation (real-time positioning) commands."""

from __future__ import annotations

from deebot_client.events import GeolocationEvent

from .common import GetEnableCommand, SetEnableCommand


class GetGeolocation(GetEnableCommand):
    """Get geolocation command."""

    NAME = "getGeolocation"
    EVENT_TYPE = GeolocationEvent


class SetGeolocation(SetEnableCommand):
    """Set geolocation command."""

    NAME = "setGeolocation"
    get_command = GetGeolocation
