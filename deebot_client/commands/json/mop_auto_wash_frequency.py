"""Mop wash info commands (wash mode, auto-wash mode and frequency)."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

from deebot_client.command import InitParam
from deebot_client.events.wash_info import MopAutoWashMode, MopWashMode
from deebot_client.messages.json.wash_info import OnWashInfo
from deebot_client.util import get_enum

from .common import JsonGetCommand, JsonSetCommand


class GetMopAutoWashFrequency(OnWashInfo, JsonGetCommand):
    """Get wash info command.

    Kept under its original name; it now reports all wash info fields.
    """

    NAME = "getWashInfo"


class SetWashInfo(JsonSetCommand):
    """Set wash info command.

    Only the given fields are sent. Note that some models (e.g. T90) only
    apply "interval" if "wiseMode" is sent in the same command.
    """

    NAME = "setWashInfo"
    get_command = GetMopAutoWashFrequency
    _mqtt_params = MappingProxyType(
        {
            "mode": InitParam(MopWashMode, optional=True),
            "wiseMode": InitParam(MopAutoWashMode, "wise_mode", optional=True),
            "interval": InitParam(int, optional=True),
        }
    )

    def __init__(
        self,
        mode: MopWashMode | str | None = None,
        wise_mode: MopAutoWashMode | str | None = None,
        interval: int | None = None,
    ) -> None:
        params: dict[str, Any] = {}
        if mode is not None:
            if isinstance(mode, str):
                mode = get_enum(MopWashMode, mode)
            params["mode"] = mode.value
        if wise_mode is not None:
            if isinstance(wise_mode, str):
                wise_mode = get_enum(MopAutoWashMode, wise_mode)
            params["wiseMode"] = wise_mode.value
        if interval is not None:
            params["interval"] = interval
        if not params:
            raise ValueError(
                "At least one of mode, wise_mode or interval must be provided."
            )
        super().__init__(params)


class SetMopAutoWashFrequency(SetWashInfo):
    """Set mop auto-wash frequency (interval only)."""

    def __init__(self, interval: int) -> None:
        super().__init__(interval=interval)
