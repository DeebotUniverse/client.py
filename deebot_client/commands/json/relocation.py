"""Relocate commands."""

from .common import ExecuteCommand


class SetRelocationState(ExecuteCommand):
    """Set relocation state command."""

    NAME = "setRelocationState"

    def __init__(self) -> None:
        super().__init__({"mode": "manu"})
