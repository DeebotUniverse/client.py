"""Battery commands."""

from deebot_client.messages.json.station_state import OnStationState

from .common import JsonCommandWithMessageHandling


class GetStationState(OnStationState, JsonCommandWithMessageHandling):
    """Get station state command."""

    NAME = "getStationState"
