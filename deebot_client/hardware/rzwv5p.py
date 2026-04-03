"""Hardware definition for Ecovacs DEEBOT T80S OMNI."""

from deebot_client.capabilities import Capabilities
from deebot_client.hardware.capabilities.battery import BatteryCapability
from deebot_client.hardware.capabilities.charge import ChargeCapability
from deebot_client.hardware.capabilities.clean import CleanCapability
from deebot_client.hardware.capabilities.clean_v2 import CleanV2Capability
from deebot_client.hardware.capabilities.map import MapCapability
from deebot_client.hardware.capabilities.stats import StatsCapability
from deebot_client.hardware.capabilities.volume import VolumeCapability
from deebot_client.hardware.capabilities.water import WaterCapability
from deebot_client.hardware.capabilities.station import StationCapability
from deebot_client.hardware.capabilities.life_span import LifeSpanCapability
from deebot_client.hardware.capabilities.wifi import WifiCapability
from deebot_client.hardware.base import AbstractDeebot

class Device(AbstractDeebot):
    """Ecovacs DEEBOT T80S OMNI."""

    @property
    def capabilities(self) -> Capabilities:
        """Return the capabilities of the device."""
        return Capabilities(
            battery=BatteryCapability(),
            charge=ChargeCapability(),
            clean=CleanCapability(),
            clean_v2=CleanV2Capability(),
            map=MapCapability(),
            stats=StatsCapability(),
            volume=VolumeCapability(),
            water=WaterCapability(),
            station=StationCapability(),
            life_span=LifeSpanCapability(),
            wifi=WifiCapability(),
        )
