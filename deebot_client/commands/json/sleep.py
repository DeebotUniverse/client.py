"""Sleep (do-not-disturb) commands."""

from __future__ import annotations

from deebot_client.events import SleepEvent

from .common import GetEnableCommand, SetEnableCommand


class GetSleep(GetEnableCommand):
    """Get sleep command."""

    NAME = "getSleep"
    EVENT_TYPE = SleepEvent


class SetSleep(SetEnableCommand):
    """Set sleep command."""

    NAME = "setSleep"
    get_command = GetSleep
