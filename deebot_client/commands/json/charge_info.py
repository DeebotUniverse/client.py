"""Charge info commands."""

from __future__ import annotations

from deebot_client.messages.json.charge_info import OnChargeInfo

from .common import JsonCommandWithMessageHandling


class GetChargeInfo(OnChargeInfo, JsonCommandWithMessageHandling):
    """Get charge info command."""

    NAME = "getChargeInfo"
