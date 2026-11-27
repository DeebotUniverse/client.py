"""Border switch commands."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import BorderSwitchEvent
from deebot_client.events.mower import BorderSwitchMode, BorderSwitchModeEvent
from deebot_client.util import get_enum

from .common import GetEnableCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus
    from deebot_client.message import HandlingResult


class GetBorderSwitch(GetEnableCommand):
    """Get border switch command."""

    NAME = "getBorderSwitch"
    EVENT_TYPE = BorderSwitchEvent

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        result = super()._handle_body_data_dict(event_bus, data)
        if (mode := data.get("mode")) is not None:
            event_bus.notify(BorderSwitchModeEvent(BorderSwitchMode(int(mode))))
        return result


class SetBorderSwitch(JsonSetCommand):
    """Set border switch command."""

    NAME = "setBorderSwitch"
    get_command = GetBorderSwitch
    _mqtt_params = MappingProxyType(
        {
            "enable": InitParam(bool),
            "mode": InitParam(BorderSwitchMode, optional=True),
        }
    )

    def __init__(self, enable: bool, mode: BorderSwitchMode | None = None) -> None:
        args: dict[str, Any] = {"enable": 1 if enable else 0}
        if mode is not None:
            args["mode"] = mode.value
        super().__init__(args)


class SetBorderSwitchMode(SetBorderSwitch):
    """Set border switch mode command. Enables the border switch too."""

    _mqtt_params = MappingProxyType(
        {"enable": None, "mode": InitParam(BorderSwitchMode)}
    )

    def __init__(self, mode: BorderSwitchMode | str) -> None:
        if isinstance(mode, str):
            mode = get_enum(BorderSwitchMode, mode)
        super().__init__(enable=True, mode=mode)
