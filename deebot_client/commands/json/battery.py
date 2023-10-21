"""Battery commands."""
from deebot_client.messages.json import OnBattery

from .common import CommandWithMessageHandling


class GetBattery(OnBattery, CommandWithMessageHandling):
    """Get battery command."""

    name = "getBattery"

    xml_name = "GetBatteryInfo"

    def __init__(self, is_available_check: bool = False) -> None:
        super().__init__()
        self._is_available_check = is_available_check
