"""WashInfo command module."""

from types import MappingProxyType
from typing import Any

from deebot_client.command import InitParam
from deebot_client.event_bus import EventBus
from deebot_client.events import WashInfoEvent, WashMode
from deebot_client.message import HandlingResult

from .common import JsonGetCommand, JsonSetCommand


class GetWashInfo(JsonGetCommand):
    """Get wash info command."""

    name = "getWashInfo"



class SetWashInfo(JsonSetCommand):
    """Set wash info command."""

    name = "setWashInfo"
    get_command = GetWashInfo
    _mqtt_params = MappingProxyType(
        {
            "mode": InitParam(int),
            "hot_wash_amount": InitParam(int),
        }
    )

    def __init__(self, mode: WashMode | str| None = None, hot_wash_amount: int | None) -> None:
        args = {}
        if isinstance(mode, str):
            mode = WashMode.get(mode)
        
        if mode is not None:
            args["mode"] = mode
            
        if hot_wash_amount is not None:
            agrs["hot_wash_amount"] = hot_wash_amount
        super().__init__(args)
