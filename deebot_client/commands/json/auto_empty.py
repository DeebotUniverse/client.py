"""Auto empty commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.auto_empty import (
    AutoEmptyEvent,
    AutoEmptyIntensity,
    Frequency,
)
from deebot_client.messages.json.auto_empty import OnAutoEmpty
from deebot_client.util import get_enum

from .common import ExecuteCommand, JsonGetCommand

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.event_bus import EventBus
    from deebot_client.message import HandlingResult
    from deebot_client.models import ApiDeviceInfo


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


class SetAutoEmptyIntensity(ExecuteCommand):
    """Set the auto empty intensity, keeping auto-empty on or off."""

    NAME = "setAutoEmpty"

    def __init__(self, intensity: AutoEmptyIntensity | str) -> None:
        if not isinstance(intensity, AutoEmptyIntensity):
            intensity = get_enum(AutoEmptyIntensity, intensity)
        super().__init__({"intensity": intensity.value})

    async def _execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[HandlingResult, dict[str, Any]]:
        # The robot rejects the change without "enable".
        last = event_bus.get_last_event(AutoEmptyEvent)
        if isinstance(self._args, dict):
            self._args["enable"] = int(bool(last.enabled)) if last else 1
        return await super()._execute(authenticator, device_info, event_bus)
