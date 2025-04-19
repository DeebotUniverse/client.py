"""XML messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from deebot_client.message import Message

__all__: Sequence[str] = []
# fmt: off
# ordered by file asc
_MESSAGES: list[type[Message]] = [
]
# fmt: on

MESSAGES: dict[str, type[Message]] = {message.NAME: message for message in _MESSAGES}
