"""Push message handlers for GOAT A3000 LiDAR mower telemetry.

The GOAT sends several unsolicited ``iot/atr/onXXX`` messages that have
no corresponding handler in the existing library messages registry:

* ``onPos`` — real-time mower position and heading, 1–2 Hz during mowing
* ``onCleanInfo`` — motion state transitions (start / pause / stop)

Without these handlers the messages are silently discarded but the
library never fires the corresponding events, so integrations cannot
track position or state in real time.

Note: ``onStats`` pushes are handled by the existing
:class:`~deebot_client.messages.json.stats.OnStats` handler, which
already supports the mower payload shape (``area`` + ``time`` fields).

All handlers reuse existing library event types to remain compatible
with the standard subscription model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import (
    Position,
    PositionsEvent,
    StateEvent,
)
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import State
from deebot_client.rs.map import PositionType

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


class OnPos(MessageBodyDataDict):
    """Handler for unsolicited ``onPos`` position push messages.

    The GOAT A3000 streams position and heading via ``iot/atr/onPos/...``
    at ~1 Hz during mowing.  Fires :class:`PositionsEvent` so that
    integrations can track the mower location in real time.

    Payload example::

        {"deebotPos": {"x": -1234, "y": 567, "a": 270, "invalid": 0},
         "chargePos": [{"x": 0, "y": 0, "a": 0}]}
    """

    NAME = "onPos"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        positions: list[Position] = []

        for type_str in ("deebotPos", "chargePos"):
            raw = data.get(type_str)
            if raw is None:
                continue

            # deebotPos is a dict; chargePos can be a list or dict
            if isinstance(raw, dict):
                items: list[Any] = [raw]
            else:
                items = raw

            for entry in items:
                if not isinstance(entry, dict):
                    continue
                if entry.get("invalid", 0):
                    continue  # GPS fix not yet valid
                try:
                    positions.append(
                        Position(
                            type=PositionType.from_str(type_str),
                            x=int(entry["x"]),
                            y=int(entry["y"]),
                            a=int(entry.get("a", 0)),
                        )
                    )
                except (KeyError, ValueError, TypeError):
                    _LOGGER.debug("onPos: could not parse entry %s", entry)

        if positions:
            event_bus.notify(PositionsEvent(positions=positions))
            return HandlingResult.success()

        return HandlingResult.analyse()


class OnCleanInfo(MessageBodyDataDict):
    """Handler for unsolicited ``onCleanInfo`` state push messages.

    The GOAT delivers motion-state transitions (start / pause / stop /
    return to dock) via this message so the integration sees state
    changes without waiting for the next poll cycle.

    Fires :class:`StateEvent`.  The mapping mirrors
    :class:`~deebot_client.commands.json.clean.GetCleanInfo`.
    """

    NAME = "onCleanInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        status: State | None = None
        state = data.get("state")

        if data.get("trigger") == "alert":
            status = State.ERROR
        elif state in ("clean", "washing"):
            clean_state = data.get("cleanState", {})
            motion_state = clean_state.get("motionState")
            if motion_state == "working":
                status = State.CLEANING
            elif motion_state == "pause":
                status = State.PAUSED
            elif motion_state == "goCharging":
                status = State.RETURNING
        elif state == "goCharging":
            status = State.RETURNING
        elif state == "idle":
            status = State.IDLE

        if status is not None:
            event_bus.notify(StateEvent(status))
            return HandlingResult.success()

        return HandlingResult.analyse()
