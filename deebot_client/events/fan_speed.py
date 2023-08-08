"""Fan speed event module."""

from dataclasses import dataclass
from enum import Enum

from ..util import DisplayNameIntEnum
from .base import Event


class FanSpeedLevel(DisplayNameIntEnum):
    """Enum class for all possible fan speed levels."""

    # Values should be sort from low to high on their meanings
    QUIET = 1000
    NORMAL = 0
    MAX = 1
    MAX_PLUS = 2


class FanSpeedLevelXml(Enum):
    # Currently used for the Deebot 900 / MQTT + XML based devices
    STRONG = 'strong'
    STANDARD = 'standard'


@dataclass(frozen=True)
class FanSpeedEvent(Event):
    """Fan speed event representation."""

    speed: FanSpeedLevel | FanSpeedLevelXml
