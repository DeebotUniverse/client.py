"""RTK status command (mowers only)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.rtk import RtkBaseStation, RtkEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import JsonCommandWithMessageHandling

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


def _coerce_base_station(raw: dict[str, Any]) -> RtkBaseStation:
    return RtkBaseStation(
        serial_number=str(raw.get("sn", "")),
        satellites_visible=int(raw.get("star", 0) or 0),
        firmware=raw.get("version"),
        state=raw.get("state"),
        mode=raw.get("mode"),
    )


class GetRtk(JsonCommandWithMessageHandling, MessageBodyDataDict):
    r"""Get RTK status command for mower devices.

    Sends ``getRTK`` to the device and notifies a :class:`RtkEvent` with
    the parsed response. The cloud payload is shaped like this (sample
    captured from a GOAT A1600 RTK on firmware 1.15.13)::

        {
            "result": 0,
            "rtks": [
                {"sn": "908276", "star": 30, "state": 0, "mode": 0,
                 "version": "...,QD302 1.3.8,...,QD302 1.3.1"}
            ],
            "observations": {
                "solStat": 0, "poseType": 50,
                "roverId": "908336", "roverSvs": 35, "roverSolnSvs": 30,
                "roverSignalRate": 44, "roverSignalScore": 90,
                "roverOcclusionRate": 8,
                "baseStnId": "\\"1544\\"", "baseSolnSvs": 29,
                "baseSignalRate": 45, "baseSignalScore": 94,
                "baseOcclusionRate": 24
            }
        }
    """

    NAME = "getRTK"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        observations = data.get("observations") or {}
        if not observations:
            return HandlingResult.analyse()

        rtks_raw = data.get("rtks") or []
        base_stations = [
            _coerce_base_station(r) for r in rtks_raw if isinstance(r, dict)
        ]

        event_bus.notify(
            RtkEvent(
                rover_serial_number=str(observations.get("roverId", "")),
                rover_satellites_visible=int(observations.get("roverSvs", 0) or 0),
                rover_satellites_used=int(observations.get("roverSolnSvs", 0) or 0),
                base_satellites_used=int(observations.get("baseSolnSvs", 0) or 0),
                rover_signal_score=int(observations.get("roverSignalScore", 0) or 0),
                base_signal_score=int(observations.get("baseSignalScore", 0) or 0),
                rover_occlusion_rate=int(
                    observations.get("roverOcclusionRate", 0) or 0
                ),
                base_occlusion_rate=int(observations.get("baseOcclusionRate", 0) or 0),
                base_stations=base_stations,
                base_station_id=observations.get("baseStnId"),
                solution_status=observations.get("solStat"),
                pose_type=observations.get("poseType"),
            )
        )
        return HandlingResult.success()
