"""Stats commands."""

from __future__ import annotations

from typing import Any

from deebot_client.events import CleanJobStatus, ReportStatsEvent, StatsEvent, TotalStatsEvent
from deebot_client.message import HandlingResult

from .common import RobotDetailGetCommand


class GetStats(RobotDetailGetCommand):
    """Get current clean stats."""

    NAME = 'getStats'
    FIELDS = ('cleanArea', 'cleanTime', 'workMode')

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus,
        data: dict[str, Any],
    ) -> HandlingResult:
        event_bus.notify(
            StatsEvent(
                area=_maybe_int(data.get('cleanArea')),
                time=_maybe_int(data.get('cleanTime')),
                type=_maybe_str(data.get('workMode')),
            )
        )
        return HandlingResult.success()


class GetReportStats(RobotDetailGetCommand):
    """Get best-effort report stats.

    Detailed clean-log decoding is not captured yet, so this surfaces a minimal
    snapshot that satisfies the capability contract and keeps the profile loadable.
    """

    NAME = 'getReportStats'
    FIELDS = ('cleanArea', 'cleanTime', 'workMode')

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus,
        data: dict[str, Any],
    ) -> HandlingResult:
        event_bus.notify(
            ReportStatsEvent(
                area=_maybe_int(data.get('cleanArea')),
                time=_maybe_int(data.get('cleanTime')),
                type=_maybe_str(data.get('workMode')),
                cleaning_id='',
                status=CleanJobStatus.NO_STATUS,
                content=[],
            )
        )
        return HandlingResult.success()


class GetTotalStats(RobotDetailGetCommand):
    """Get best-effort lifetime stats."""

    NAME = 'getTotalStats'
    FIELDS = ('cleanArea', 'cleanTime', 'cleanCount')

    @classmethod
    def _handle_body_data_dict(
        cls,
        event_bus,
        data: dict[str, Any],
    ) -> HandlingResult:
        event_bus.notify(
            TotalStatsEvent(
                area=int(data.get('cleanArea', 0) or 0),
                time=int(data.get('cleanTime', 0) or 0),
                cleanings=int(data.get('cleanCount', 0) or 0),
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
