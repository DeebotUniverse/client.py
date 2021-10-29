"""Maps commands."""
import logging

from ..command import Command

_LOGGER = logging.getLogger(__name__)


class GetCachedMapInfo(Command):
    """Get cached map info command."""

    name = "getCachedMapInfo"

    def __init__(self) -> None:
        super().__init__()


class GetMapTrace(Command):
    """Get map trace command."""

    TRACE_POINT_COUNT = 200

    name = "getMapTrace"

    def __init__(self, trace_start: int = 0) -> None:
        super().__init__(
            {"pointCount": self.TRACE_POINT_COUNT, "traceStart": trace_start},
        )


class GetMinorMap(Command):
    """Get minor map command."""

    name = "getMinorMap"

    def __init__(self, *, map_id: int, piece_index: int) -> None:
        super().__init__({"mid": map_id, "type": "ol", "pieceIndex": piece_index})


class GetMapSet(Command):
    """Get map set command."""

    name = "getMapSet"

    def __init__(self, map_id: str) -> None:
        super().__init__({"mid": map_id, "type": "ar"})


class GetMapSubSet(Command):
    """Get map subset command."""

    name = "getMapSubSet"

    def __init__(
        self, *, map_id: str, map_set_id: str, map_type: str, map_subset_id: str
    ) -> None:
        super().__init__(
            {
                "mid": map_id,
                "msid": map_set_id,
                "type": map_type,
                "mssid": map_subset_id,
            },
        )


class GetPos(Command):
    """Get position command."""

    name = "getPos"

    def __init__(self) -> None:
        super().__init__(["chargePos", "deebotPos"])


class GetMajorMap(Command):
    """Get major map command."""

    name = "getMajorMap"

    def __init__(self) -> None:
        super().__init__()
