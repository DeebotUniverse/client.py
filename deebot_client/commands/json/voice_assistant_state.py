"""Voice assistant state command module."""

from __future__ import annotations

from deebot_client.events import VoiceAssistantStateEvent

from .common import GetEnableCommand, SetEnableCommand


class GetVoiceAssistantState(GetEnableCommand):
    """Get voice assistant state command."""

    NAME = "getVoiceAssistantState"
    EVENT_TYPE = VoiceAssistantStateEvent


class SetVoiceAssistantState(SetEnableCommand):
    """Set voice assistant state command."""

    NAME = "setVoiceAssistantState"
    get_command = GetVoiceAssistantState
