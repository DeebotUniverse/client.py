"""Smart mowing with avoidance commands."""

from __future__ import annotations

from deebot_client.events import HumanoidAiEvent

from .common import GetEnableCommand, SetEnableCommand


class GetHumanoidAi(GetEnableCommand):
    """Get smart mowing with avoidance state."""

    NAME = "getHumanoidAI"
    EVENT_TYPE = HumanoidAiEvent


class SetHumanoidAi(SetEnableCommand):
    """Set smart mowing with avoidance state."""

    NAME = "setHumanoidAI"
    get_command = GetHumanoidAi
