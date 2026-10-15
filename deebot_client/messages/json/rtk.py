"""RTK messages."""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING, Any

from deebot_client.events.mower import RtkBaseStationEvent, RtkFixType, RtkSignalEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnRtk(MessageBodyDataDict):
    """On RTK message.

    The push message contains only the base station,
    the get response contains additionally the signal observations.
    """

    NAME = "onRTK"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        handled = False
        if stations := data.get("rtks"):
            station = stations[0]
            position = None
            x, y = float(station.get("x", 0)), float(station.get("y", 0))
            # 0,0 is reported without a connection to the station
            if x or y:
                position = (x, y)
            event_bus.notify(
                RtkBaseStationEvent(
                    state=int(station["state"]),
                    satellites=int(station["star"]),
                    position=position,
                )
            )
            handled = True

        if observations := data.get("observations"):
            fix_type: RtkFixType | int = int(observations["poseType"])
            with suppress(ValueError):
                fix_type = RtkFixType(fix_type)
            event_bus.notify(
                RtkSignalEvent(
                    fix_type=fix_type,
                    rover_satellites=int(observations["roverSolnSvs"]),
                    rover_signal_score=int(observations["roverSignalScore"]),
                    rover_occlusion_rate=int(observations["roverOcclusionRate"]),
                    base_satellites=int(observations["baseSolnSvs"]),
                    base_signal_score=int(observations["baseSignalScore"]),
                    base_occlusion_rate=int(observations["baseOcclusionRate"]),
                )
            )
            handled = True

        return HandlingResult.success() if handled else HandlingResult.analyse()
