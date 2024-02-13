"""ClearMap commands."""
from __future__ import annotations

from .common import ExecuteCommand


class ClearMap(ExecuteCommand):
    """ClearMap state command."""

    name = "clearMap"

    def __init__(self) -> None:
        super().__init__({"type": "all"})
