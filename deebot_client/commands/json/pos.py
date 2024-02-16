"""Position command module."""
from __future__ import annotations

from deebot_client.messages.json import OnPos

from .common import JsonCommandWithMessageHandling


class GetPos(JsonCommandWithMessageHandling, OnPos):
    """Get position command."""

    name = "getPos"

    def __init__(self) -> None:
        super().__init__(["chargePos", "deebotPos"])
