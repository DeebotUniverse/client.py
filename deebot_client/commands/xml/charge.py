"""Charge command."""

from __future__ import annotations

from .common import ExecuteCommand


class Charge(ExecuteCommand):
    """Charge command."""

    NAME = "Charge"
    HAS_SUB_ELEMENT = True

    def __init__(self) -> None:
        # example: <ctl><charge type='go'/></ctl>
        super().__init__({"type": "go"})
