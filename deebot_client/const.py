"""Constants module."""
from __future__ import annotations

from enum import Enum, StrEnum
from typing import Self

REALM = "ecouser.net"
PATH_API_APPSVR_APP = "appsvr/app.do"
PATH_API_PIM_PRODUCT_IOT_MAP = "pim/product/getProductIotMap"
PATH_API_IOT_DEVMANAGER = "iot/devmanager.do"
PATH_API_LG_LOG = "lg/log.do"
REQUEST_HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 5.1.1; A5010 Build/LMY48Z)",
}
COUNTRY_CHINA = "CN"


class DataType(StrEnum):
    """Data type."""

    JSON = "j"
    XML = "x"

    @classmethod
    def get(cls, value: str) -> Self | None:
        """Return DataType or None for given value."""
        try:
            return cls(value.lower())
        except ValueError:
            return None


class UndefinedType(Enum):
    """Singleton type for use with not set sentinel values."""

    _singleton = 0


UNDEFINED = UndefinedType._singleton  # pylint: disable=protected-access  # noqa: SLF001

# from https://github.com/mrbungle64/ecovacs-deebot.js/blob/master/library/errorCodes.json
ERROR_CODES = {
    -3: "Error parsing response data",
    -2: "Internal error",
    -1: "Host not reachable or communication malfunction",
    0: "NoError: Robot is operational",
    3: "RequestOAuthError: Authentication error",
    7: "log data is not found",
    100: "NoError: Robot is operational",
    101: "BatteryLow: Low battery",
    102: "HostHang: Robot is off the floor",
    103: "WheelAbnormal: Driving Wheel malfunction",
    104: "DownSensorAbnormal: Excess dust on the Anti-Drop Sensors",
    105: "Stuck: Robot is stuck",
    106: "SideBrushExhausted: Side Brushes have expired",
    107: "DustCaseHeapExhausted: Dust case filter expired",
    108: "SideAbnormal: Side Brushes are tangled",
    109: "RollAbnormal: Main Brush is tangled",
    110: "NoDustBox: Dust Bin Not installed",
    111: "BumpAbnormal: Bump sensor stuck",
    112: 'LDS: LDS "Laser Distance Sensor" malfunction',
    113: "MainBrushExhausted: Main brush has expired",
    114: "DustCaseFilled: Dust bin full",
    115: "BatteryError:",
    116: "ForwardLookingError:",
    117: "GyroscopeError:",
    118: "StrainerBlock:",
    119: "FanError:",
    120: "WaterBoxError:",
    201: "AirFilterUninstall:",
    202: "UltrasonicComponentAbnormal",
    203: "SmallWheelError",
    204: "WheelHang",
    205: "IonSterilizeExhausted",
    206: "IonSterilizeAbnormal",
    207: "IonSterilizeFault",
    312: "Please replace the Dust Bag.",
    404: "Recipient unavailable",
    500: "Request Timeout",
    601: "ERROR_ClosedAIVISideAbnormal",
    602: "ClosedAIVIRollAbnormal",
}
