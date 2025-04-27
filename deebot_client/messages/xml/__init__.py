"""XML messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.messages.xml.battery import BatteryInfo
from deebot_client.messages.xml.charge_state import ChargeState
from deebot_client.messages.xml.map import MapP, Trace
from deebot_client.messages.xml.pos import Pos

if TYPE_CHECKING:
    from collections.abc import Sequence

    from deebot_client.message import Message

__all__: Sequence[str] = ["BatteryInfo", "ChargeState", "MapP", "Pos", "Trace"]
# fmt: off
# ordered by file asc
_MESSAGES: list[type[Message]] = [
    BatteryInfo,

    ChargeState,

    MapP,
    Trace,

    Pos
]
# fmt: on

MESSAGES: dict[str, type[Message]] = {message.NAME: message for message in _MESSAGES}
