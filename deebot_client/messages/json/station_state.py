"""Base station messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.station import State, StationErrorEvent, StationEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


def _parse_error_codes(value: Any) -> tuple[int, ...] | None:
    """Return the station error codes, or None when no codes are usable.

    An empty list means "no current errors" and clears a previously reported
    fault. None means the error channel is absent, is not a list, or held no
    usable code -- the last known fault must be preserved rather than cleared.
    """
    if not isinstance(value, list):
        return None

    codes: list[int] = []
    for entry in value:
        if isinstance(entry, bool):
            continue
        if isinstance(entry, int):
            codes.append(entry)
        elif isinstance(entry, str):
            try:
                codes.append(int(entry))
            except ValueError:
                continue

    if value and not codes:
        # A non-empty list with nothing usable is "unknown", not "all clear".
        return None
    return tuple(codes)


class OnStationState(MessageBodyDataDict):
    """On station state message."""

    NAME = "onStationState"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        # "body":{"data":{"content":{"error":[],"type":0},"state":0},"code":0,"msg":"ok"} - Idle
        # "body":{"data":{"content":{"error":[],"type":1,"motionState":1},"state":1},"code":0,"msg":"ok"} - Emptying
        # "body":{"data":{"content":{"error":[],"type":2,"motionState":1},"state":1},"code":0,"msg":"ok"} - Drying mop
        content = data.get("content")
        if isinstance(content, dict):
            # Report station errors first, so an unrecognised activity state
            # cannot swallow a water-tank or other station fault.
            errors = _parse_error_codes(content.get("error"))
            if errors is not None:
                event_bus.notify(StationErrorEvent(errors))

        if (state := data.get("state")) == 0:
            reported_state = State.IDLE
        elif (
            state == 1
            and content
            and content.get("type") == 1
            and content.get("motionState") == 1
        ):
            reported_state = State.EMPTYING_DUSTBIN
        elif (
            state == 1
            and content
            and content.get("type") == 2
            and content.get("motionState") == 1
        ):
            reported_state = State.DRYING_MOP
        else:
            return HandlingResult.analyse()

        event_bus.notify(StationEvent(reported_state))
        return HandlingResult.success()
