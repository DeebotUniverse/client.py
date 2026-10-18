"""Border spin messages."""

from __future__ import annotations

from deebot_client.events import BorderSpinEvent

from .common import OnEnableMessage


class OnBorderSpin(OnEnableMessage):
    """On border spin message."""

    NAME = "onBorderSpin"
    EVENT_TYPE = BorderSpinEvent
