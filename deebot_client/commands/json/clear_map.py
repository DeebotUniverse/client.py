"""ClearMap commands."""

from .common import ExecuteCommand


class ClearMap(ExecuteCommand):
    """ClearMap state command."""

    NAME = "clearMap"

    def __init__(self) -> None:
        super().__init__({"type": "all"})
