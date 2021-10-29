"""clean log commands."""
import logging
from typing import Any, Dict, List, Optional

from ..events import CleanLogEntry, CleanLogEventDto
from .common import CommandWithHandling, EventBus

_LOGGER = logging.getLogger(__name__)


class GetCleanLogs(CommandWithHandling):
    """Get clean logs command."""

    name = "GetCleanLogs"

    def __init__(self, count: int = 0) -> None:
        super().__init__({"count": count})

    def handle_requested(self, event_bus: EventBus, response: Dict[str, Any]) -> bool:
        """Handle response from a manual requested command.

        :return: True if data was valid and no error was included
        """
        if response.get("ret") == "ok":
            resp_logs: Optional[List[dict]] = response.get("logs")

            # Ecovacs API is changing their API, this request may not working properly
            if resp_logs is not None and len(resp_logs) >= 0:
                logs: List[CleanLogEntry] = []
                for log in resp_logs:
                    logs.append(
                        CleanLogEntry(
                            timestamp=log.get("ts"),
                            image_url=log.get("imageUrl"),
                            type=log.get("type"),
                            area=log.get("area"),
                            stop_reason=log.get("stopReason"),
                            total_time=log.get("last"),
                        )
                    )

                event_bus.notify(CleanLogEventDto(logs))
                return True

        _LOGGER.warning("Could not parse clean logs event with %s", response)
        return False

    @classmethod
    def handle(cls, event_bus: EventBus, message: Dict[str, Any]) -> bool:
        """Handle message and notify the correct event subscribers.

        :return: True if data was valid and no error was included
        """
        _LOGGER.error("Not supported by %s", cls.name)
        return False
