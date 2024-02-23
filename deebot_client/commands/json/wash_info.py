"""WashInfo command module."""
from __future__ import annotations

from types import MappingProxyType
from typing import Any

from deebot_client.command import InitParam
from deebot_client.events import WashMode
from deebot_client.messages.json.wash_info import OnWashInfo

from .common import JsonGetCommand, JsonSetCommand


class GetWashInfo(OnWashInfo, JsonGetCommand):
    """Get wash info command."""

    name = "getWashInfo"


class SetWashInfo(JsonSetCommand):
    """Set wash info command."""

    name = "setWashInfo"
    get_command = GetWashInfo
    _mqtt_params = MappingProxyType(
        {
            "mode": InitParam(int, default=None),
            "hot_wash_amount": InitParam(int, default=None),
        }
    )

    def __init__(
        self,
        mode: WashMode | str | int | None = None,
        hot_wash_amount: int | None = None,
    ) -> None:
        args: dict[str, Any] = {}

        if isinstance(mode, str):
            mode = WashMode.get(mode)
        if isinstance(mode, WashMode):
            mode = mode.value

        if mode is not None:
            args["mode"] = mode

        if hot_wash_amount is not None:
            args["hot_wash_amount"] = hot_wash_amount
        super().__init__(args)
