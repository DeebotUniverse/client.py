"""Battery commands."""
from ..messages import OnBattery
from .common import _NoArgsCommand


class GetBattery(OnBattery, _NoArgsCommand):
    """Get battery command."""

    name = "getBattery"
