"""Mower charge activity messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.capabilities import DeviceType
from deebot_client.events import StateEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import State

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnChargeInfo(MessageBodyDataDict):
    """Mower returning and work-completion notifications."""

    NAME = "onChargeInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        if event_bus.capabilities.device_type is not DeviceType.MOWER:
            return HandlingResult.analyse()
        if data.get("trigger") == "alert":
            event_bus.notify(StateEvent(State.ERROR))
        elif data.get("state") == "goCharging":
            event_bus.notify(StateEvent(State.RETURNING))
        elif data.get("state") == "idle":
            # Idle alone does not prove docking. Query charge and clean state.
            event_bus.request_refresh(StateEvent, queue_if_busy=True)
        else:
            return HandlingResult.analyse()
        return HandlingResult.success()
