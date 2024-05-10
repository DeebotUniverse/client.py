"""Constants module."""

from __future__ import annotations

from enum import Enum, StrEnum
from typing import Self

REALM = "ecouser.net"
PATH_API_APPSVR_APP = "appsvr/app.do"
PATH_API_PIM_PRODUCT_IOT_MAP = "pim/product/getProductIotMap"
PATH_API_IOT_DEVMANAGER = "iot/devmanager.do"
PATH_API_LG_LOG = "lg/log.do"
PATH_API_USERS_USER = "users/user.do"
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
    1: "Request error",
    3: "RequestOAuthError: Authentication error",
    5: "Access denied",
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
    112: "LDS: LDS \"Laser Distance Sensor\" malfunction",
    113: "MainBrushExhausted: Main brush has expired",
    114: "DustCaseFilled: Dust bin full",
    115: "BatteryError:",
    116: "ForwardLookingError:",
    117: "GyroscopeError:",
    118: "StrainerBlock:",
    119: "FanError:",
    120: "WaterBoxError:",
    121: "PlateJammed:",
    125: "Reservoir malfunction",
    126: "Reservoir is not installed",
    128: "Mopping Pad Plates are not both installed",
    129: "Mopping Pad Plate is tangled",
    201: "AirFilterUninstall:",
    202: "UltrasonicComponentAbnormal",
    203: "SmallWheelError",
    204: "WheelHang",
    205: "IonSterilizeExhausted",
    206: "IonSterilizeAbnormal",
    207: "IonSterilizeFault",
    209: "D-ToF Sensor malfunction",
    301: "FreshWaterBox empty",
    302: "WasteWaterBox full",
    303: "FreshWaterBox missing",
    304: "WasteWaterBox missing",
    305: "Dirty Water Tank is full",
    306: "Cleaning Sink Filter is not installed",
    307: "Auto-Clean Station malfunction",
    308: "Communication Malfunction",
    310: "Lid open",
    311: "Replace the Dust Bag",
    312: "TODO: unknown",
    313: "TODO: unknown",
    314: "Water Supply Module or Silver Ion Sterilization module is not installed",
    315: "Water Supply Module is not installed",
    316: "Clean silk is full",
    317: "Clean Water Tank refill malfunction",
    318: "Dirty Water Tank is full",
    319: "Cleaning solution is running low",
    404: "Recipient unavailable",
    500: "Request Timeout",
    601: "ERROR_ClosedAIVISideAbnormal",
    602: "ClosedAIVIRollAbnormal",
    1007: "Mop plugged",
    1021: "Cleaning complete",
    1024: "Low battery, returning to charge",
    1027: "Unable de find the charging dock, returning to starting position",
    1052: "Time to change the mop",
    1053: "Task interrupted, returning to charge",
    1061: "Resuming cleaning after position retrieved",
    1062: "Unable de locate, starting new map",
    1068: "Failed to find position, returning to charge",
    1071: "Position updated",
    1094: "AirDrying mop",
    1088: "Failed to find position",
    2036: "Obstacle detected",
    2079: "TODO: unknown",
    4200: "Robot not reachable",
    20003: "Task type not supported",
    20011: "Handle deal message fail",
    20012: "Get point count out of range",
}
