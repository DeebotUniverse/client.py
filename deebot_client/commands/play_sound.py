"""Play sound commands."""

from .common import _ExecuteCommand


class PlaySound(_ExecuteCommand):
    """Play sound command."""

    name = "playSound"

    def __init__(self) -> None:
        super().__init__({"count": 1, "sid": 30})
