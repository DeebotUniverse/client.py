"""clean log commands."""
from typing import Any

from deebot_client.authentication import Authenticator
from deebot_client.command import CommandResult
from deebot_client.const import PATH_API_LG_LOG, REQUEST_HEADERS
from deebot_client.events import CleanJobStatus, CleanLogEntry, CleanLogEvent
from deebot_client.events.event_bus import EventBus
from deebot_client.logging_filter import get_logger
from deebot_client.models import DeviceInfo

from .common import JsonCommand

_LOGGER = get_logger(__name__)


class GetCleanLogs(JsonCommand):
    """Get clean logs command."""

    _targets_bot: bool = False
    name = "GetCleanLogs"

    xml_name = "GetCleanLogs"

    def __init__(self, count: int = 0) -> None:
        super().__init__({"count": count})

    async def _execute_api_request(
        self, authenticator: Authenticator, device_info: DeviceInfo
    ) -> dict[str, Any]:
        json = {
            "td": self.name,
            "did": device_info.did,
            "resource": device_info.resource,
        }

        credentials = await authenticator.authenticate()
        query_params = {
            "td": json["td"],
            "u": credentials.user_id,
            "cv": "1.67.3",
            "t": "a",
            "av": "1.3.1",
        }

        return await authenticator.post_authenticated(
            PATH_API_LG_LOG,
            json,
            query_params=query_params,
            headers=REQUEST_HEADERS,
        )

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        if response["ret"] == "ok":
            resp_logs: list[dict] | None = response.get("logs")

            # Ecovacs API is changing their API, this request may not work properly
            if resp_logs is not None and len(resp_logs) >= 0:
                logs: list[CleanLogEntry] = []
                for log in resp_logs:
                    try:
                        logs.append(
                            CleanLogEntry(
                                timestamp=log["ts"],
                                image_url=log["imageUrl"],
                                type=log["type"],
                                area=log["area"],
                                stop_reason=CleanJobStatus(
                                    int(log.get("stopReason", -2))
                                ),
                                duration=log["last"],
                            )
                        )
                    except Exception:  # pylint: disable=broad-except
                        _LOGGER.warning("Skipping log entry: %s", log, exc_info=True)

                event_bus.notify(CleanLogEvent(logs))
                return CommandResult.success()

        return CommandResult.analyse()
