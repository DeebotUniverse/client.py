"""Play sound commands."""

from .common import ExecuteCommand


class PlaySound(ExecuteCommand):
    """Play sound command."""

    name = "playSound"

    xml_name = "PlaySound"

    def __init__(self) -> None:
        super().__init__({"count": 1, "sid": 30})
