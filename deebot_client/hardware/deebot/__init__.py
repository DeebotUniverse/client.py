"""Hardware deebot module."""
import importlib
import pkgutil
import sys
from threading import Lock

from deebot_client.capabilities import Capabilities
from deebot_client.exceptions import DeebotError
from deebot_client.logging_filter import get_logger

__all__ = ["get_capabilities"]

_LOGGER = get_logger(__name__)


FALLBACK = "fallback"

DEVICES: dict[str, Capabilities] = {}
_IMPORT_LOCK = Lock()


def _load() -> None:
    for _, package_name, _ in pkgutil.iter_modules(__path__):
        full_package_name = f"{__package__}.{package_name}"
        if full_package_name not in sys.modules:
            importlib.import_module(full_package_name)


def get_capabilities(class_: str) -> Capabilities:
    """Get capabilities for given class."""
    if not DEVICES:
        with _IMPORT_LOCK:
            if not DEVICES:
                _load()
                if not DEVICES:
                    raise DeebotError("Could not load devices.")

    if device := DEVICES.get(class_):
        return device

    _LOGGER.debug("No capabilities found for %s. Using fallback.", class_)
    return DEVICES[FALLBACK]
