"""Play sound commands."""

from .common import ExecuteCommand


class PlaySound(ExecuteCommand):
    """Play sound command."""

    NAME = "PlaySound"

    def __init__(self) -> None:
        super().__init__({"sid": "30"})
