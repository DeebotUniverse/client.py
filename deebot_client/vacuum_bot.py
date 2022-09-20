"""Vacuum bot module."""
import asyncio
import inspect
import re
from typing import Any, Final

from .api_client import ApiClient
from .command import Command
from .commands import COMMANDS_WITH_HANDLING, Clean
from .commands.clean import CleanAction
from .events import (
    CleanLogEvent,
    CustomCommandEvent,
    LifeSpanEvent,
    PositionsEvent,
    PositionType,
    StatsEvent,
    StatusEvent,
    TotalStatsEvent,
)
from .events.event_bus import EventBus
from .logging_filter import get_logger
from .map import Map
from .message import Message
from .messages import MESSAGES
from .models import DeviceInfo, VacuumState

_LOGGER = get_logger(__name__)

_COMMAND_REPLACE_PATTERN = "^((on)|(off)|(report))"
_COMMAND_REPLACE_REPLACEMENT = "get"


class VacuumBot:
    """Vacuum bot representation."""

    def __init__(
        self,
        device_info: DeviceInfo,
        api_client: ApiClient,
    ):
        self.device_info: Final[DeviceInfo] = device_info
        self._api_client = api_client
        self._authenticator = api_client._authenticator

        self._semaphore = asyncio.Semaphore(3)
        self._status: StatusEvent = StatusEvent(device_info.status == 1, None)

        self.fw_version: str | None = None
        self.events: Final[EventBus] = EventBus(self.execute_command)

        self.map: Final[Map] = Map(self.execute_command, self.events)

        async def on_pos(event: PositionsEvent) -> None:
            if self._status == StatusEvent(True, VacuumState.DOCKED):
                return

            deebot = next(p for p in event.positions if p.type == PositionType.DEEBOT)

            if deebot:
                on_charger = filter(
                    lambda p: p.type == PositionType.CHARGER
                    and p.x == deebot.x
                    and p.y == deebot.y,
                    event.positions,
                )
                if on_charger:
                    # deebot on charger so the status should be docked... Checking
                    self.events.request_refresh(StatusEvent)

        self.events.subscribe(PositionsEvent, on_pos)

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

        async def on_custom_command(event: CustomCommandEvent) -> None:
            await self.handle_message(event.name, event.response)

        self.events.subscribe(CustomCommandEvent, on_custom_command)

    async def execute_command(self, command: Command) -> None:
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
            await command.execute(self._authenticator, self.device_info, self.events)

    def set_available(self, available: bool) -> None:
        """Set available."""
        status = StatusEvent(available, self._status.state)
        self.events.notify(status)

    async def handle_message(
        self, message_name: str, message_data: dict[str, Any]
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

        # Handle message starting with "on","off","report" the same as "get" commands
        converted_name = re.sub(
            _COMMAND_REPLACE_PATTERN,
            _COMMAND_REPLACE_REPLACEMENT,
            message_name,
        )

        # T8 series and newer
        if converted_name.endswith("_V2"):
            converted_name = converted_name[:-3]

        found_command = MESSAGES.get(
            converted_name, COMMANDS_WITH_HANDLING.get(converted_name, None)
        )
        if found_command:
            if issubclass(found_command, Message):
                _LOGGER.debug("Falling back to old handling way for %s", message_name)
                found_command.handle(self.events, message_data)
            else:
                _LOGGER.debug('Command "%s" doesn\'t support message handling', converted_name)
        else:
            _LOGGER.debug('Unknown message "%s" with %s', message_name, message_data)
