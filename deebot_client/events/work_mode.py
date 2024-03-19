"""Work mode event module."""

from __future__ import annotations

from dataclasses import dataclass

from deebot_client.util import DisplayNameIntEnum

from .base import Event


class WorkMode(DisplayNameIntEnum):
    """Enum class for all possible work modes."""

    VACUUM_AND_MOP = 0
    VACUUM = 1
    MOP = 2
    MOP_AFTER_VACUUM = 3


@dataclass(frozen=True)
class WorkModeEvent(Event):
    """Work mode event representation."""

    mode: WorkMode
