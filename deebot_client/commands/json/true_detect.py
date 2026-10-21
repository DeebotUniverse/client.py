"""True detect command module."""

from __future__ import annotations

from types import MappingProxyType

from deebot_client.command import InitParam
from deebot_client.events import TrueDetectEvent

from .common import GetEnableCommand, JsonSetCommand, SetEnableCommand


class GetTrueDetect(GetEnableCommand):
    """Get multimap state command."""

    NAME = "getTrueDetect"
    EVENT_TYPE = TrueDetectEvent


class SetTrueDetect(SetEnableCommand):
    """Set multimap state command."""

    NAME = "setTrueDetect"
    get_command = GetTrueDetect


class SetTrueDetectWithLevel(JsonSetCommand):
    """Set TrueDetect including the level field.

    Some firmwares reject the standard ``{"enable": 1}`` payload with a
    ``format error`` and require the ``level`` field returned by
    :class:`GetTrueDetect` to be included as well.
    """

    NAME = "setTrueDetect"
    get_command = GetTrueDetect
    _mqtt_params = MappingProxyType(
        {
            "enable": InitParam(bool, "enable"),
            "level": InitParam(int, "level", optional=True),
        }
    )

    def __init__(self, enable: bool, level: int = 1) -> None:
        super().__init__({"enable": 1 if enable else 0, "level": level})
