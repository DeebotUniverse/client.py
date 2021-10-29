"""Play sound commands."""
import logging

from .common import _ExecuteCommand

_LOGGER = logging.getLogger(__name__)


class PlaySound(_ExecuteCommand):
    """Play sound command."""

    name = "playSound"

    def __init__(self) -> None:
        super().__init__({"count": 1, "sid": 30})
