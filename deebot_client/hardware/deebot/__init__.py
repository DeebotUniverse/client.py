"""Hardware deebot module."""

from __future__ import annotations

import asyncio
import importlib
import pkgutil
from typing import TYPE_CHECKING

from deebot_client.logging_filter import get_logger

if TYPE_CHECKING:
    from deebot_client.capabilities import Capabilities
    from deebot_client.models import StaticDeviceInfo

__all__ = ["get_static_device_info"]

_LOGGER = get_logger(__name__)


FALLBACK = "fallback"

DEVICES: dict[str, StaticDeviceInfo[Capabilities]] = {}


def _load() -> None:
    for _, package_name, _ in pkgutil.iter_modules(__path__):
        full_package_name = f"{__package__}.{package_name}"
        importlib.import_module(full_package_name)


async def get_static_device_info(class_: str) -> StaticDeviceInfo[Capabilities]:
    """Get static device info for given class."""
    if not DEVICES:
        await asyncio.get_event_loop().run_in_executor(None, _load)

    if device := DEVICES.get(class_):
        _LOGGER.debug("Capabilities found for %s", class_)
        return device

    _LOGGER.info(
        "No capabilities found for %s, therefore not all features are available. trying to use fallback...",
        class_,
    )
    return DEVICES[FALLBACK]
