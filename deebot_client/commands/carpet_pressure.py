"""Carpet pressure command module."""

from ..events import CarpetPressureEvent
from .common import SetEnableCommand, _GetEnableCommand


class GetCarpetPressure(_GetEnableCommand):
    """Get carpet pressure command."""

    name = "getCarpertPressure"
    event_type = CarpetPressureEvent


class SetCarpetPressure(SetEnableCommand):
    """Set carpet pressure command."""

    name = "setCarpertPressure"
    get_command = GetCarpetPressure
