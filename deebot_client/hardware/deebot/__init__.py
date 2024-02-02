"""Hardware deebot module."""
from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deebot_client.models import StaticDeviceInfo

__all__ = ["get_static_device_info"]

_LOGGER = logging.getLogger(__name__)


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
        _LOGGER.debug("Capabilities found for %s", class_)
        return device

    _LOGGER.info(
        "No capabilities found for %s, therefore not all features are available. trying to use fallback...",
        class_,
    )
    return DEVICES[FALLBACK]
