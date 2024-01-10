"""Battery commands."""
from deebot_client.messages.xml import OnBattery

from .common import XmlCommandWithMessageHandling


class GetBattery(OnBattery, XmlCommandWithMessageHandling):
    """Get battery command."""

    name = "GetBatteryInfo"

    def __init__(self, *, is_available_check: bool = False) -> None:
        super().__init__()
        self._is_available_check = is_available_check
