"""Auto empty commands."""

from __future__ import annotations

from typing import Any

from deebot_client.events.auto_empty import Frequency
from deebot_client.messages.json.auto_empty import OnAutoEmpty
from deebot_client.util import get_enum

from .common import ExecuteCommand, JsonGetCommand

__all__ = [
    "GetAutoEmpty",
    "SetAutoEmpty",
]


class GetAutoEmpty(OnAutoEmpty, JsonGetCommand):
    """Get auto empty command."""

    name = "getAutoEmpty"


class SetAutoEmpty(ExecuteCommand):
    """Set auto empty command."""

    name = "setAutoEmpty"

    def __init__(self, frequency: Frequency | str) -> None:
        if not isinstance(frequency, Frequency):
            frequency = get_enum(Frequency, frequency)

        is_on = frequency is not Frequency.OFF
        params: dict[str, Any] = {"enable": is_on}
        if is_on:
            params["frequency"] = frequency.value
        super().__init__(params)
