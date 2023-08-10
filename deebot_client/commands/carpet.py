"""Carpet pressure command module."""

from ..events import CarpetAutoFanBoostEvent
from .common import GetEnableCommand, SetEnableCommand


class GetCarpetAutoFanBoost(GetEnableCommand):
    """Get carpet auto fan boost command."""

    name = "getCarpertPressure"

    # TODO Potentially not available on XML based models?
    xml_name = "GetCarpertPressure"

    event_type = CarpetAutoFanBoostEvent


class SetCarpetAutoFanBoost(SetEnableCommand):
    """Set carpet auto fan boost command."""

    name = "setCarpertPressure"

    # TODO Potentially not available on XML based models?
    xml_name = "GetCarpertPressure"

    get_command = GetCarpetAutoFanBoost
