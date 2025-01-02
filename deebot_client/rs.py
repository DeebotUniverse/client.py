"""Funtions written in Rust."""

from __future__ import annotations

from deebot_client import _rs

from ._rs import *  # noqa: F403

__doc__ = _rs.__doc__
if hasattr(_rs, "__all__"):
    __all__ = _rs.__all__
