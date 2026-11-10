"""Area parameter command module."""

from __future__ import annotations

from deebot_client.messages.json.area_parameter import OnAreaParameter

from .common import JsonGetCommand


class GetAreaParameter(OnAreaParameter, JsonGetCommand):
    """Get parameters for mower areas."""

    NAME = "getAreaParameter"
