"""Ota messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import OtaEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnOta(MessageBodyDataDict):
    """On ota message."""

    NAME = "onOta"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        ota_event = OtaEvent(
            support_auto=bool(data.get("supportAuto", False)),
            auto_enabled=bool(data.get("autoSwitch", False)),
            version=data.get("cver") or data.get("ver"),
            status=data.get("status"),
            progress=data.get("progress"),
        )
        event_bus.notify(ota_event)
        return HandlingResult.success()
