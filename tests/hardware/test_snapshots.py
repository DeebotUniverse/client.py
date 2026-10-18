"""Snapshot tests of all hardware profiles."""

from __future__ import annotations

import dataclasses
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import pytest

from deebot_client import hardware
from deebot_client.command import Command

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion

_HARDWARE_DIR = Path(hardware.__file__).parent
_PROFILES = sorted(
    file.stem
    for file in _HARDWARE_DIR.iterdir()
    if file.suffix == ".py" and file.name != "__init__.py"
)


def _serialize(value: Any) -> Any:
    """Return a readable and stable representation of a capability value."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _serialize(field_value)
            for field in dataclasses.fields(value)
            if field.init and (field_value := getattr(value, field.name)) is not None
        }
    if isinstance(value, dict | MappingProxyType):
        return {_serialize(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        items = [_serialize(item) for item in value]
        return sorted(items) if isinstance(value, set | frozenset) else items
    return _serialize_leaf(value)


def _serialize_leaf(value: Any) -> Any:
    if isinstance(value, Command):
        # e.g. GetBattery(is_available_check=True) keeps the flag outside _args
        extra = "".join(
            f", {name.lstrip('_')}={attr!r}"
            for name, attr in vars(value).items()
            if name != "_args" and attr
        )
        return f"{type(value).__name__}({value._args!r}{extra})"
    if isinstance(value, Enum):
        return f"{type(value).__name__}.{value.name}"
    if isinstance(value, type) or callable(value):
        return value.__qualname__
    return value


@pytest.mark.parametrize("class_", _PROFILES)
async def test_hardware_profile(class_: str, snapshot: SnapshotAssertion) -> None:
    """Snapshot each profile, so capability changes are visible in review.

    Aliases are symlinks to another profile and are recorded as such.
    """
    path = _HARDWARE_DIR / f"{class_}.py"
    if path.is_symlink():
        assert {"alias_of": path.resolve().stem} == snapshot
        return

    device_info = await hardware.get_static_device_info(class_)
    assert device_info is not None
    assert _serialize(device_info) == snapshot
