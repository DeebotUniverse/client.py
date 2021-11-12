"""Advanced mode command module."""

from ..events import CarpetPressureEvent
from .common import _GetEnabledCommand, _SetEnabledCommand


class GetCarpetPressure(_GetEnabledCommand):
    """Get carpet pressure command."""

    name = "getCarpertPressure"
    event_type = CarpetPressureEvent


class SetCarpetPressure(_SetEnabledCommand):
    """Set carpet pressure command."""

    name = "setCarpertPressure"
    get_command = GetCarpetPressure
