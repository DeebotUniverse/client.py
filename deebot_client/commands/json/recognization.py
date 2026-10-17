"""AI recognition commands."""

from __future__ import annotations

from deebot_client.events import AiRecognitionEvent

from .common import GetEnableCommand, SetEnableCommand


class GetRecognization(GetEnableCommand):
    """Get AI recognition state."""

    NAME = "getRecognization"
    EVENT_TYPE = AiRecognitionEvent
    _field_name = "state"


class SetRecognization(SetEnableCommand):
    """Set AI recognition state."""

    NAME = "setRecognization"
    get_command = GetRecognization
    _field_name = "state"
