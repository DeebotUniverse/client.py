"""Protection state events."""

from __future__ import annotations

from dataclasses import dataclass

from .base import Event


@dataclass(frozen=True, kw_only=True)
class ProtectStateEvent(Event):
    """Raw boolean protection states reported by the device."""

    is_anim_protect: bool
    is_rain_protect: bool
    is_rain_delay: bool
    is_e_stop: bool
    is_locked: bool
    is_pin_code: bool
    is_prepare_data_success: bool
