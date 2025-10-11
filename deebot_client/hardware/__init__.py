"""Hardware module."""

from __future__ import annotations

import asyncio
import importlib
from typing import TYPE_CHECKING, cast

from deebot_client.logging_filter import get_logger

if TYPE_CHECKING:
    from deebot_client.models import StaticDeviceInfo

__all__ = ["get_static_device_info"]

_LOGGER = get_logger(__name__)


_DEVICES: dict[str, StaticDeviceInfo] = {}
_NOT_FOUND: set[str] = set()


async def get_static_device_info(class_: str) -> StaticDeviceInfo | None:
    """Get static device info for given class."""
    # Check if already loaded
    if device := _DEVICES.get(class_):
        _LOGGER.debug("Capabilities found for %s", class_)
        return device

    # Check if we already know it doesn't exist
    if class_ in _NOT_FOUND:
        return None

    # Try to load just this specific module
    try:
        full_package_name = f"{__package__}.{class_}"
        module = await asyncio.to_thread(importlib.import_module, full_package_name)
    except ModuleNotFoundError:
        _LOGGER.debug("No capabilities found for %s", class_)
        _NOT_FOUND.add(class_)
        return None

    # Get device info from the module's get_device_info function
    # This function is guaranteed to exist via a pytest test
    device = cast("StaticDeviceInfo", module.get_device_info())
    _DEVICES[class_] = device
    _LOGGER.debug("Capabilities found for %s", class_)
    return device
