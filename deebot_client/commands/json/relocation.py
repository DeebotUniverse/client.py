"""Relocate commands."""
from .common import ExecuteCommand


class SetRelocationState(ExecuteCommand):
    """Set relocation state command."""

    name = "setRelocationState"

    xml_name = "SetRelocationState"

    def __init__(self) -> None:
        super().__init__({"mode": "manu"})
