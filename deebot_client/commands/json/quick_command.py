"""Quick command commands (called "Scenario Cleaning" in the app)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import ScenariosEvent
from deebot_client.message import HandlingResult, MessageBodyDataList
from deebot_client.models import Scenario

from .common import JsonCommandWithMessageHandling

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetQuickCommand(JsonCommandWithMessageHandling, MessageBodyDataList):
    """Get quick command (scenario) list command."""

    NAME = "getQuickCommand"

    def __init__(self) -> None:
        # Same types as requested by the app
        super().__init__({"type": "1,2,4"})

    @classmethod
    def _handle_body_data_list(
        cls, event_bus: EventBus, data: list[dict[str, Any]]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        scenarios = [
            Scenario(
                id=str(item["qcid"]),
                name=item["name"],
                map_id=str(item.get("mid", group.get("mid", ""))),
            )
            for group in data
            for item in group.get("array", [])
        ]
        event_bus.notify(ScenariosEvent(scenarios))
        return HandlingResult.success()
