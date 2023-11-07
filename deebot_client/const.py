"""Constants module."""

from enum import StrEnum
from typing import Self

REALM = "ecouser.net"
PATH_API_APPSVR_APP = "appsvr/app.do"
PATH_API_PIM_PRODUCT_IOT_MAP = "pim/product/getProductIotMap"
PATH_API_IOT_DEVMANAGER = "iot/devmanager.do"
PATH_API_LG_LOG = "lg/log.do"
PATH_API_DLN_LOG_LIST = "log/clean_result/list"
REQUEST_HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 5.1.1; A5010 Build/LMY48Z)",
}


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
