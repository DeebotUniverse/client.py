"""Carpet pressure command module."""

from ..events import CarpetAutoFanBoostEvent
from .common import GetEnableCommand, SetEnableCommand


class GetCarpetAutoFanBoost(GetEnableCommand):
    """Get carpet auto fan boost command."""

    name = "getCarpertPressure"
    event_type = CarpetAutoFanBoostEvent


class SetCarpetAutoFanBoost(SetEnableCommand):
    """Set carpet auto fan boost command."""

    name = "setCarpertPressure"
    get_command = GetCarpetAutoFanBoost
