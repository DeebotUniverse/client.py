"""Json messages."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .battery import OnBattery
from .charge_state import OnChargeState
from .clean import OnCleanInfo, OnCleanInfoV2
from .error import OnError
from .map import OnMapSetV2, OnMapTrace, OnMinorMap
from .pos import OnPos
from .stats import OnStats, ReportStats

if TYPE_CHECKING:
    from deebot_client.message import Message

__all__ = [
    "OnBattery",
    "OnCleanInfo",
    "OnCleanInfoV2",
    "OnError",
    "OnMapSetV2",
    "OnMapTrace",
    "OnMinorMap",
    "OnPos",
    "OnStats",
    "OnChargeState",
    "ReportStats",
]

# fmt: off
# ordered by file asc
_MESSAGES: list[type[Message]] = [
    OnBattery,
    OnCleanInfo,
    OnCleanInfoV2,
    OnError,
    OnMapSetV2,
    OnMapTrace,
    OnMinorMap,
    OnPos,
    OnStats,
    OnChargeState,

    ReportStats
]
# fmt: on

MESSAGES: dict[str, type[Message]] = {message.name: message for message in _MESSAGES}  # type: ignore[misc]
