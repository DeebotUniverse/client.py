"""Hardware deebot module."""
import importlib
import pkgutil

from deebot_client.logging_filter import get_logger
from deebot_client.models import StaticDeviceInfo

__all__ = ["get_static_device_info"]

_LOGGER = get_logger(__name__)


FALLBACK = "fallback"

DEVICES: dict[str, StaticDeviceInfo] = {}


def _load() -> None:
    for _, package_name, _ in pkgutil.iter_modules(__path__):
        full_package_name = f"{__package__}.{package_name}"
        importlib.import_module(full_package_name)


def get_static_device_info(class_: str) -> StaticDeviceInfo:
    """Get static device info for given class."""
    if not DEVICES:
        _load()

    if device := DEVICES.get(class_):
        return device

    _LOGGER.debug("No capabilities found for %s. Using fallback.", class_)
    return DEVICES[FALLBACK]
