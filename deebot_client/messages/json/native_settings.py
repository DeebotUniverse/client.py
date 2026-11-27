"""Native settings parser helper (childLock, autoBoost, breakClean, disturb, volume)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import (
    CarpetAutoFanBoostEvent,
    ChildLockEvent,
    ContinuousCleaningEvent,
    DoNotDisturbEvent,
    VolumeEvent,
)

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

__all__ = ["handle_native_settings"]


def handle_native_settings(event_bus: EventBus, data: dict[str, Any]) -> None:
    """Notify setting events for native Y1 settings in reports / 10001 queries.

    Requires strict boolean flags for switch settings and non-boolean int in
    range 0..10 for volume. Absent, unknown, or malformed fields are ignored.
    """
    if "childLock" in data:
        child_lock = data["childLock"]
        if isinstance(child_lock, bool):
            event_bus.notify(ChildLockEvent(child_lock))

    if "autoBoost" in data:
        auto_boost = data["autoBoost"]
        if isinstance(auto_boost, bool):
            event_bus.notify(CarpetAutoFanBoostEvent(auto_boost))

    if "breakCleanSwitch" in data:
        break_clean = data["breakCleanSwitch"]
        if isinstance(break_clean, bool):
            event_bus.notify(ContinuousCleaningEvent(break_clean))

    if "disturbSwitch" in data:
        disturb = data["disturbSwitch"]
        if isinstance(disturb, bool):
            event_bus.notify(DoNotDisturbEvent(disturb))

    if "volume" in data:
        volume = data["volume"]
        if (
            not isinstance(volume, bool)
            and isinstance(volume, int)
            and 0 <= volume <= 10
        ):
            event_bus.notify(VolumeEvent(volume, 10))
