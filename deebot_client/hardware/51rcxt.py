"""Ecovacs GOAT A3000 LiDAR Pro (51rcxt) capabilities.

The GOAT A3000 LiDAR Pro shares the same firmware stack, protocol and
capabilities as the GOAT A3000 LiDAR (cr0e4u).  Both models use the
``cleanMower`` command format, the ``onMI``/``onArI`` zone-map protocol,
and identical mower settings.

This module delegates to the cr0e4u definition so both device classes
share a single source of truth.
"""

from __future__ import annotations

from deebot_client.models import StaticDeviceInfo

from .cr0e4u import get_device_info as _cr0e4u_get_device_info


def get_device_info() -> StaticDeviceInfo:
    """Get device info for the GOAT A3000 LiDAR Pro (51rcxt)."""
    return _cr0e4u_get_device_info()
