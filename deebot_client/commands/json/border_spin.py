"""Border spin commands."""

from __future__ import annotations

from deebot_client.messages.json.border_spin import OnBorderSpin

from .common import GetEnableCommand, SetEnableCommand


class GetBorderSpin(OnBorderSpin, GetEnableCommand):
    """Get border spin command."""

    NAME = "getBorderSpin"


class SetBorderSpin(SetEnableCommand):
    """Set border spin command."""

    NAME = "setBorderSpin"
    get_command = GetBorderSpin
