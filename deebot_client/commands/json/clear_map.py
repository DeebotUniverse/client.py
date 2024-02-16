"""Clear map commands."""
from __future__ import annotations

from .common import ExecuteCommand


class ClearMap(ExecuteCommand):
    """Clear map command."""

    name = "clearMap"

    def __init__(self) -> None:
        super().__init__({"type": "all"})
