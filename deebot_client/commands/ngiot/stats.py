"""Stats commands."""

from __future__ import annotations

from typing import Any

from deebot_client.events import CleanJobStatus, ReportStatsEvent, StatsEvent, TotalStatsEvent
from deebot_client.message import HandlingResult

from .common import RobotDetailGetCommand


class GetStats(RobotDetailGetCommand):
    """Get current clean stats.

    eyfj07 reports cleanTime in minutes. Home Assistant's Ecovacs duration
    sensors expect native seconds, so convert before emitting the event.
    """

    NAME = "getStats"
    FIELDS = ("cleanArea", "cleanTime", "cleanCount", "workMode", "cleanLogReport")

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus,
        data: dict[str, Any],
    ) -> HandlingResult:
        event_bus.notify(
            StatsEvent(
                area=_maybe_int(data.get("cleanArea")),
                time=_minutes_to_seconds(data.get("cleanTime")),
                type=_maybe_str(data.get("workMode")),
            )
        )
        return HandlingResult.success()


class GetReportStats(RobotDetailGetCommand):
    """Get current clean report stats from the robot detail snapshot."""

    NAME = "getReportStats"
    FIELDS = ("cleanArea", "cleanTime", "cleanCount", "workMode", "cleanLogReport")

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus,
        data: dict[str, Any],
    ) -> HandlingResult:
        clean_log_report = data.get("cleanLogReport")
        cleaning_id = ""
        if isinstance(clean_log_report, dict):
            cleaning_id = str(clean_log_report.get("cid") or "")

        event_bus.notify(
            ReportStatsEvent(
                area=_maybe_int(data.get("cleanArea")),
                time=_minutes_to_seconds(data.get("cleanTime")),
                type=_maybe_str(data.get("workMode")),
                cleaning_id=cleaning_id,
                status=CleanJobStatus.NO_STATUS,
                content=[],
            )
        )
        return HandlingResult.success()


class GetTotalStats(RobotDetailGetCommand):
    """Get lifetime totals.

    eyfj07 exposes lifetime totals on the total-stats response surface as
    ``cleanAreaTotal``, ``cleanTimeTotal``, and ``cleanCountTotal``.

    cleanTimeTotal is reported in minutes. Home Assistant expects native
    duration values in seconds, so convert before emitting TotalStatsEvent.
    """

    NAME = "getTotalStats"
    FIELDS = ("cleanAreaTotal", "cleanTimeTotal", "cleanCountTotal")

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus,
        data: dict[str, Any],
    ) -> HandlingResult:
        event_bus.notify(
            TotalStatsEvent(
                area=_coerce_total(data, "cleanAreaTotal", "cleanArea"),
                time=_minutes_to_seconds(
                    data.get("cleanTimeTotal", data.get("cleanTime", 0))
                )
                or 0,
                cleanings=_coerce_total(data, "cleanCountTotal", "cleanCount"),
            )
        )
        return HandlingResult.success()


def _maybe_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None



def _maybe_str(value: Any) -> str | None:
    return None if value is None else str(value)



def _coerce_total(data: dict[str, Any], primary: str, fallback: str) -> int:
    value = data.get(primary, data.get(fallback, 0))
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0



def _minutes_to_seconds(value: Any) -> int | None:
    minutes = _maybe_int(value)
    if minutes is None:
        return None
    return minutes * 60