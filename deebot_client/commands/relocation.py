"""Relocate commands."""
from .common import _ExecuteCommand


class SetRelocationState(_ExecuteCommand):
    """Set relocation state command."""

    name = "setRelocationState"

    def __init__(self) -> None:
        super().__init__({"mode": "manu"})
