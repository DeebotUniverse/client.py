"""clean log commands."""
import logging
from typing import Any, Dict, List, Optional

from ..events import CleanJobStatus, CleanLogEntry, CleanLogEventDto
from ..message import MessageResponse
from .common import CommandWithHandling, EventBus

_LOGGER = logging.getLogger(__name__)


class GetCleanLogs(CommandWithHandling):
    """Get clean logs command."""

    name = "GetCleanLogs"

    def __init__(self, count: int = 0) -> None:
        super().__init__({"count": count})

    def handle_requested(
        self, event_bus: EventBus, response: Dict[str, Any]
    ) -> MessageResponse:
        """Handle response from a manual requested command.

        :return: A message response
        """
        if response["ret"] == "ok":
            resp_logs: Optional[List[dict]] = response.get("logs")

            # Ecovacs API is changing their API, this request may not working properly
            if resp_logs is not None and len(resp_logs) >= 0:
                logs: List[CleanLogEntry] = []
                for log in resp_logs:
                    logs.append(
                        CleanLogEntry(
                            timestamp=log["ts"],
                            image_url=log["imageUrl"],
                            type=log["type"],
                            area=log["area"],
                            stop_reason=CleanJobStatus(int(log["stopReason"])),
                            duration=log["last"],
                        )
                    )

                event_bus.notify(CleanLogEventDto(logs))
                return MessageResponse.success()

        return MessageResponse.analyse()

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: Dict[str, Any]) -> MessageResponse:
        raise RuntimeError("Should never be called!")
