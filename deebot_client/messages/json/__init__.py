"""Json messages."""

from __future__ import annotations

import re

from deebot_client.logging_filter import get_logger
from deebot_client.message import Message

from .auto_empty import OnAutoEmpty
from .battery import OnBattery
from .gps_position import OnGpsPos
from .map import OnCachedMapInfo, OnMajorMap, OnMapInfoV2, OnMapSetV2
from .station_state import OnStationState
from .stats import OnStats, ReportStats
from .work_state import OnWorkState

_LOGGER = get_logger(__name__)

__all__ = [
    "OnBattery",
    "OnCachedMapInfo",
    "OnGpsPos",
    "OnMajorMap",
    "OnMapInfoV2",
    "OnMapSetV2",
    "OnStats",
    "OnWorkState",
    "ReportStats",
]

# fmt: off
# ordered by file asc
_MESSAGES: list[type[Message]] = [
    OnAutoEmpty,

    OnBattery,

    OnGpsPos,

    OnCachedMapInfo,
    OnMajorMap,
    OnMapInfoV2,
    OnMapSetV2,

    OnStationState,

    OnStats,
    ReportStats,

    OnWorkState,
]
# fmt: on

MESSAGES: dict[str, type[Message]] = {message.NAME: message for message in _MESSAGES}

_MAP_LEGACY_COMMANDS = frozenset(
    {
        "getCachedMapInfo",
        "getMapSet",
        "getMapSubSet",
        "getMapTrace",
        "getMinorMap",
        "getMultiMapState",
    }
)

_LEGACY_USE_GET_COMMAND = _MAP_LEGACY_COMMANDS | frozenset(
    {
        "getAdvancedMode",
        "getBreakPoint",
        "getCarpertPressure",
        "getChargeState",
        "getCleanCount",
        "getCleanInfo",
        "getCleanPreference",
        "getEfficiency",
        "getError",
        "getLifeSpan",
        "getNetInfo",
        "getPos",
        "getSpeed",
        "getSweepMode",
        "getTotalStats",
        "getTrueDetect",
        "getVoiceAssistantState",
        "getVolume",
        "getWaterInfo",
        "getWorkMode",
    }
)


def get_legacy_message(
    message_name: str,
    converted_name: str,
    *,
    has_map: bool = True,
) -> type[Message] | None:
    """Try to find the message for the given name using legacy way."""
    # Handle message starting with "on","off","report" the same as "get" commands
    converted_name = re.sub(
        "^((on)|(off)|(report))",
        "get",
        converted_name,
    )

    if converted_name not in _LEGACY_USE_GET_COMMAND:
        _LOGGER.debug('Unknown message "%s"', message_name)
        return None

    if not has_map and converted_name in _MAP_LEGACY_COMMANDS:
        _LOGGER.debug(
            'Skipping legacy map fallback for "%s" on device without map capability',
            message_name,
        )
        return None

    from deebot_client.commands.json import (  # noqa: PLC0415
        COMMANDS,
    )

    if found_command := COMMANDS.get(converted_name, None):
        if issubclass(found_command, Message):
            _LOGGER.debug("Falling back to legacy way for %s", message_name)
            return found_command

        _LOGGER.debug('Command "%s" doesn\'t support message handling', converted_name)

    return None
