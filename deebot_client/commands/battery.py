"""Battery commands."""
from ..messages import OnBattery
from .common import NoArgsCommand


class GetBattery(OnBattery, NoArgsCommand):
    """Get battery command."""

    name = "getBattery"

    def __init__(self, is_available_check: bool = False) -> None:
        super().__init__()
        self._is_available_check = is_available_check
