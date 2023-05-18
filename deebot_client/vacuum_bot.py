"""Vacuum bot module."""
import asyncio
import inspect
import json
from typing import Any, Final

from deebot_client.mqtt_client import MqttClient, SubscriberInfo

from .authentication import Authenticator
from .command import Command
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
from .messages import get_message
from .models import DeviceInfo, VacuumState

_LOGGER = get_logger(__name__)


class VacuumBot:
    """Vacuum bot representation."""

    def __init__(
        self,
        device_info: DeviceInfo,
        authenticator: Authenticator,
    ):
        self.device_info: Final[DeviceInfo] = device_info
        self._authenticator = authenticator

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
            self._handle_message(event.name, event.response)

        self.events.subscribe(CustomCommandEvent, on_custom_command)

    async def execute_command(self, command: Command) -> None:
        """Execute given command."""
        async with self._semaphore:
            await command.execute(self._authenticator, self.device_info, self.events)

    async def subscribe_to(self, client: MqttClient) -> None:
        """Subscribe bot to mqtt."""
        await client.subscribe(
            SubscriberInfo(self.device_info, self.events, self._handle_message)
        )

    def set_available(self, available: bool) -> None:
        """Set available."""
        status = StatusEvent(available, self._status.state)
        self.events.notify(status)

    def _handle_message(
        self, message_name: str, message_data: str | bytes | bytearray | dict[str, Any]
    ) -> None:
        """Handle the given message.

        :param message_name: message name
        :param message_data: message data
        :return: None
        """
        try:
            _LOGGER.debug("Try to handle message %s: %s", message_name, message_data)

            if message := get_message(message_name):
                if isinstance(message_data, dict):
                    data = message_data
                else:
                    data = json.loads(message_data)

                message.handle(self.events, data)

                fw_version = data.get("header", {}).get("fwVer", None)
                if fw_version:
                    self.fw_version = fw_version
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error(
                "An exception occurred during handling message", exc_info=True
            )
