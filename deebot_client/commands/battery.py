"""Battery commands."""
from ..messages import OnBattery
from .common import NoArgsCommand


class GetBattery(OnBattery, NoArgsCommand):
    """Get battery command."""

    name = "getBattery"
