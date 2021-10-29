"""Relocate commands."""
import logging

from .common import _ExecuteCommand

_LOGGER = logging.getLogger(__name__)


class SetRelocationState(_ExecuteCommand):
    """Set relocation state command."""

    name = "setRelocationState"

    def __init__(self) -> None:
        super().__init__({"mode": "manu"})
