"""Vacuum bot module."""
import asyncio
import inspect
import re
from typing import Any, Dict, Final, Optional, Union

import aiohttp

from .api_client import ApiClient
from .command import Command
from .commands import Clean, CommandWithHandling
from .commands.clean import CleanAction
from .commands.custom import CustomCommand
from .events import (
    CleanLogEvent,
    LifeSpanEvent,
    StatsEvent,
    StatusEvent,
    TotalStatsEvent,
)
from .events.event_bus import EventBus
from .logging_filter import get_logger
from .map import Map
from .message import HandlingState
from .messages import MESSAGES
from .models import DeviceInfo, VacuumState

_LOGGER = get_logger(__name__)

_COMMAND_REPLACE_PATTERN = "^((on)|(off)|(report))"
_COMMAND_REPLACE_REPLACEMENT = "get"


class VacuumBot:
    """Vacuum bot representation."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        device_info: DeviceInfo,
        api_client: ApiClient,
    ):
        self._session = session
        self.device_info: Final[DeviceInfo] = device_info
        self._api_client = api_client

        self._semaphore = asyncio.Semaphore(3)
        self._status: StatusEvent = StatusEvent(device_info.status == 1, None)

        self.fw_version: Optional[str] = None
        self.events: Final[EventBus] = EventBus(self.execute_command)

        self.map: Final[Map] = Map(self.execute_command, self.events)

        async def on_status(event: StatusEvent) -> None:
            last_status = self._status
            self._status = event
            if (not last_status.available) and event.available:
                # bot was unavailable
                for name, obj in inspect.getmembers(
                    self.events, lambda obj: isinstance(obj, EventBus)
                ):
                    if name != "status":
                        obj.request_refresh()
            elif event.state == VacuumState.DOCKED:
                self.events.request_refresh(CleanLogEvent)
                self.events.request_refresh(TotalStatsEvent)

        self.events.subscribe(StatusEvent, on_status)

        async def on_stats(_: StatsEvent) -> None:
            self.events.request_refresh(LifeSpanEvent)

        self.events.subscribe(StatsEvent, on_stats)

    async def execute_command(self, command: Union[Command, CustomCommand]) -> None:
        """Execute given command and handle response."""
        if (
            command == Clean(CleanAction.RESUME)
            and self._status.state != VacuumState.PAUSED
        ):
            command = Clean(CleanAction.START)
        elif (
            command == Clean(CleanAction.START)
            and self._status.state == VacuumState.PAUSED
        ):
            command = Clean(CleanAction.RESUME)

        async with self._semaphore:
            response = await self._api_client.send_command(command, self.device_info)

        _LOGGER.debug("Handle command %s: %s", command.name, response)
        if isinstance(command, (CommandWithHandling, CustomCommand)):
            result = command.handle_requested(self.events, response)
            if isinstance(command, CustomCommand):
                # Custom command can be send for implemented commands too.
                # We handle the response explicit to fire event if necessary
                await self.handle_message(command.name, response)

            if result.state == HandlingState.SUCCESS and result.requested_commands:
                # Execute command which are requested by the handler
                tasks = []
                for requested_command in result.requested_commands:
                    tasks.append(
                        asyncio.create_task(self.execute_command(requested_command))
                    )

                await asyncio.gather(*tasks)
        else:
            _LOGGER.warning("Unsupported command! Command %s", command.name)

    def set_available(self, available: bool) -> None:
        """Set available."""
        status = StatusEvent(available, self._status.state)
        self.events.notify(status)

    async def handle_message(
        self, message_name: str, message_data: Dict[str, Any]
    ) -> None:
        """Handle the given message.

        :param message_name: message name
        :param message_data: message data
        :return: None
        """
        _LOGGER.debug("Handle message %s: %s", message_name, message_data)
        fw_version = message_data.get("header", {}).get("fwVer", None)
        if fw_version:
            self.fw_version = fw_version

        message_type = MESSAGES.get(message_name, None)
        if message_type:
            message_type.handle(self.events, message_data)
            return

        _LOGGER.debug("Falling back to old handling way...")
        # Handle message starting with "on","off","report" the same as "get" commands
        message_name = re.sub(
            _COMMAND_REPLACE_PATTERN,
            _COMMAND_REPLACE_REPLACEMENT,
            message_name,
        )

        # T8 series and newer
        if message_name.endswith("_V2"):
            message_name = message_name[:-3]

        found_command = MESSAGES.get(message_name, None)
        if found_command:
            found_command.handle(self.events, message_data)
        else:
            _LOGGER.debug('Unknown message "%s" with %s', message_name, message_data)
