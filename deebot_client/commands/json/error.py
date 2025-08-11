"""Error commands."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from deebot_client.const import ERROR_CODES, PATH_API_IOT_CONTROL
from deebot_client.events import ErrorEvent, StateEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import State

from .common import ExecuteCommand, JsonCommandWithMessageHandling

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.command import CommandResult
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo

_LOGGER = get_logger(__name__)


class GetError(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get error command."""

    NAME = "getError"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        codes = data.get("code")
        if not isinstance(codes, list):
            return HandlingResult.analyse()

        error: int | None = 0

        background_tasks = set()
        if 505 in codes:
            _LOGGER.debug("Clearing error 505")
            task = asyncio.create_task(
                SetError(505).execute(
                    event_bus.authenticator, event_bus.device_info, event_bus
                )
            )
            background_tasks.add(task)
            task.add_done_callback(background_tasks.discard)

        if codes:
            # the last error code
            error = codes[-1]

        if error is not None:
            description = ERROR_CODES.get(error)
            if error != 0:
                event_bus.notify(StateEvent(State.ERROR))
            event_bus.notify(ErrorEvent(error, description))
            return HandlingResult.success()

        return HandlingResult.analyse()


class SetError(ExecuteCommand):
    """SetError state command."""

    NAME = "setError"

    def __init__(self, code: int) -> None:
        super().__init__({"act": "remove", "code": [code]})
        self._api_path = PATH_API_IOT_CONTROL

    async def execute(
        self,
        authenticator: Authenticator,
        device_info: ApiDeviceInfo,
        event_bus: EventBus,
    ) -> tuple[CommandResult, dict[str, Any]]:
        """Execute the command to set an error state."""
        return await super()._execute(authenticator, device_info, event_bus)
