"""Error commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar
from weakref import WeakKeyDictionary

from deebot_client.capabilities import DeviceType
from deebot_client.const import ERROR_CODES
from deebot_client.events import ErrorEvent, StateEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import State

from .common import JsonCommandWithMessageHandling

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetError(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get error command."""

    NAME = "getError"
    _recovery_requested: ClassVar[WeakKeyDictionary[EventBus, StateEvent]] = (
        WeakKeyDictionary()
    )

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        codes = data.get("code")
        if not isinstance(codes, list):
            return HandlingResult.analyse()

        error: int | None = 0

        if codes:
            # the last error code
            error = codes[-1]

        if error is not None:
            previous_state = event_bus.get_last_event(StateEvent)
            description = ERROR_CODES.get(error)
            if error != 0:
                cls._recovery_requested.pop(event_bus, None)
                event_bus.notify(StateEvent(State.ERROR))
            event_bus.notify(ErrorEvent(error, description))
            if (
                error == 0
                and event_bus.capabilities.device_type is DeviceType.MOWER
                and previous_state == StateEvent(State.ERROR)
                and cls._recovery_requested.get(event_bus) is not previous_state
            ):
                # EventBus retains the same event object until activity changes.
                # Query once per ERROR episode, even if the cached code was zero.
                cls._recovery_requested[event_bus] = previous_state
                event_bus.request_refresh(StateEvent, queue_if_busy=True)
            return HandlingResult.success()

        return HandlingResult.analyse()
