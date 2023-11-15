"""clean log commands."""
import json
from typing import Any

from deebot_client.authentication import Authenticator
from deebot_client.command import CommandResult
from deebot_client.const import PATH_API_DLN_LOG_LIST, REQUEST_HEADERS
from deebot_client.event_bus import EventBus
from deebot_client.events import CleanJobStatus, CleanLogEntry, CleanLogEvent
from deebot_client.logging_filter import get_logger
from deebot_client.models import DeviceInfo

from .common import JsonCommand

_LOGGER = get_logger(__name__)


class GetCleanLogsV2(JsonCommand):
    """Get clean logs command."""

    _targets_bot: bool = False
    name = "clean"

    def __init__(self, count: int = 0) -> None:
        super().__init__({"count": count})

    async def _execute_api_request(
        self, authenticator: Authenticator, device_info: DeviceInfo
    ) -> dict[str, Any]:
        credentials = await authenticator.authenticate()

        query_params = {
            "did": device_info.did,
            "res": device_info.resource,
            "version": "v2",
            "logType": self.name,
            "channel": "google_play",
            "size": "10",
            "auth": json.dumps(
                {
                    "with": "users",
                    "userid": credentials.user_id,
                    "realm": "ecouser.net",
                    "token": credentials.token,
                    "resource": device_info.resource,
                }
            ),
            # "country": "DE",
            # "lang": "EN",
            # "defaultLang": "zh_cn",
            # "before": "1698540667000",
            # "et1": "1698540667778",
        }

        return await authenticator.post_authenticated(
            PATH_API_DLN_LOG_LIST,
            json={},
            query_params=query_params,
            headers=REQUEST_HEADERS,
        )

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        # Ecovacs API is changing their API, this request may not work properly
        if (
            response["code"] == 0
            and (resp_logs := response.get("data"))
            and len(resp_logs) >= 0
        ):
            logs: list[CleanLogEntry] = []
            for log in resp_logs:
                try:
                    logs.append(
                        CleanLogEntry(
                            timestamp=log["ts"],
                            image_url=log["imageUrl"],
                            type=log["type"],
                            area=log["area"],
                            stop_reason=CleanJobStatus(int(log.get("stopReason", -2))),
                            duration=log["last"],
                        )
                    )
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.warning("Skipping log entry: %s", log, exc_info=True)

            event_bus.notify(CleanLogEvent(logs))
            return CommandResult.success()

        return CommandResult.analyse()
