"""Carpet pressure command module."""

from deebot_client.events import CarpetAutoFanBoostEvent

from .common import GetEnableCommand, SetEnableCommand


class GetCarpetAutoFanBoost(GetEnableCommand):
    """Get carpet auto fan boost command."""

    NAME = "getCarpertPressure"
    EVENT_TYPE = CarpetAutoFanBoostEvent


class SetCarpetAutoFanBoost(SetEnableCommand):
    """Set carpet auto fan boost command."""

    NAME = "setCarpertPressure"
    get_command = GetCarpetAutoFanBoost
