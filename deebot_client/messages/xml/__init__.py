"""XML messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.messages.xml.battery import BatteryInfo
from deebot_client.messages.xml.charge import ChargeState
from deebot_client.messages.xml.clean import CleanReport, CleanSt
from deebot_client.messages.xml.map import MapP
from deebot_client.messages.xml.pos import Pos
from deebot_client.messages.xml.water_info import WaterBoxInfo

if TYPE_CHECKING:
    from deebot_client.message import Message

__all__ = [
    "BatteryInfo",
    "ChargeState",
    "CleanReport",
    "CleanSt",
    "MapP",
    "Pos",
    "WaterBoxInfo",
]
# fmt: off
# ordered by file asc
_MESSAGES: list[type[Message]] = [
    BatteryInfo,
    ChargeState,
    CleanReport,
    WaterBoxInfo,
    Pos,
    MapP,
    CleanSt
]
# fmt: on

MESSAGES: dict[str, type[Message]] = {message.NAME: message for message in _MESSAGES}
