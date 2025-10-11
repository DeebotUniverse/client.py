"""Auto empty commands."""

from __future__ import annotations

from typing import Any

from deebot_client.events.auto_empty import Frequency
from deebot_client.messages.json.auto_empty import OnAutoEmpty
from deebot_client.util import get_enum

from .common import ExecuteCommand, JsonGetCommand


class GetAutoEmpty(OnAutoEmpty, JsonGetCommand):
    """Get auto empty command."""

    NAME = "getAutoEmpty"


class SetAutoEmpty(ExecuteCommand):
    """Set auto empty command."""

    NAME = "setAutoEmpty"

    def __init__(
        self, enable: bool | None = None, frequency: Frequency | str | None = None
    ) -> None:
        if frequency is not None and not isinstance(frequency, Frequency):
            frequency = get_enum(Frequency, frequency)

        params: dict[str, Any] = {}
        if enable is not None:
            params["enable"] = int(enable)
        if frequency:
            params["frequency"] = frequency.value
        super().__init__(params)
