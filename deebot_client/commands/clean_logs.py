"""clean log commands."""
from typing import Any, Optional

from ..events import CleanJobStatus, CleanLogEntry, CleanLogEvent
from ..exceptions import DeebotError
from ..message import HandlingResult
from .common import CommandResult, CommandWithHandling, EventBus


class GetCleanLogs(CommandWithHandling):
    """Get clean logs command."""

    name = "GetCleanLogs"

    def __init__(self, count: int = 0) -> None:
        super().__init__({"count": count})

    def handle_requested(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a manual requested command.

        :return: A message response
        """
        if response["ret"] == "ok":
            resp_logs: Optional[list[dict]] = response.get("logs")

            # Ecovacs API is changing their API, this request may not working properly
            if resp_logs is not None and len(resp_logs) >= 0:
                logs: list[CleanLogEntry] = []
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

                event_bus.notify(CleanLogEvent(logs))
                return CommandResult.success()

        return CommandResult.analyse()

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        raise DeebotError("Should never be called!")
