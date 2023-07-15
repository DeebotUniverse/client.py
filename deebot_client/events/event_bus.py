"""Event emitter module."""
import asyncio
import threading
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, Final, Generic, TypeVar

from ..logging_filter import get_logger
from ..models import VacuumState
from ..util import cancel, create_task
from . import AvailabilityEvent, Event, StateEvent

if TYPE_CHECKING:
    from ..command import Command

_LOGGER = get_logger(__name__)

T = TypeVar("T", bound=Event)


class _EventProcessingData(Generic[T]):
    """Data class, which holds all needed data per EventDto."""

    def __init__(self) -> None:
        super().__init__()

        self.subscriber_callbacks: Final[
            list[Callable[[T], Coroutine[Any, Any, None]]]
        ] = []
        self.semaphore: Final = asyncio.Semaphore(1)
        self.last_event: T | None = None


class EventBus:
    """A very simple event bus system."""

    def __init__(
        self,
        execute_command: Callable[["Command"], Coroutine[Any, Any, None]],
    ):
        self._event_processing_dict: dict[type[Event], _EventProcessingData] = {}
        self._lock = threading.Lock()
        self._tasks: set[asyncio.Future[Any]] = set()

        self._execute_command: Final = execute_command

    def has_subscribers(self, event: type[T]) -> bool:
        """Return True, if emitter has subscribers."""
        return (
            len(self._event_processing_dict[event].subscriber_callbacks) > 0
            if event in self._event_processing_dict
            else False
        )

    def subscribe(
        self,
        event_type: type[T],
        callback: Callable[[T], Coroutine[Any, Any, None]],
    ) -> Callable[[], None]:
        """Subscribe to event."""
        event_processing_data = self._get_or_create_event_processing_data(event_type)

        def unsubscribe() -> None:
            event_processing_data.subscriber_callbacks.remove(callback)

        event_processing_data.subscriber_callbacks.append(callback)

        if event_processing_data.last_event:
            # Notify subscriber directly with the last event
            create_task(self._tasks, callback(event_processing_data.last_event))
        elif len(event_processing_data.subscriber_callbacks) == 1:
            # first subscriber therefore do refresh
            self.request_refresh(event_type)

        return unsubscribe

    def notify(self, event: T) -> bool:
        """Notify subscriber with given event representation."""
        event_processing_data = self._get_or_create_event_processing_data(type(event))

        if (
            isinstance(event, StateEvent)
            and event.state == VacuumState.IDLE
            and event_processing_data.last_event
            and event_processing_data.last_event.state == VacuumState.DOCKED  # type: ignore[attr-defined]
        ):
            # todo distinguish better between docked and idle and outside event bus. # pylint: disable=fixme
            # Problem getCleanInfo will return state=idle, when bot is charging
            event = StateEvent(VacuumState.DOCKED)  # type: ignore[assignment]
        elif (
            isinstance(event, AvailabilityEvent)
            and event.available
            and event_processing_data.last_event
            and not event_processing_data.last_event.available  # type: ignore[attr-defined]
        ):
            # unavailable -> available: refresh everything
            for event_type, _ in self._event_processing_dict.items():
                if event_type != AvailabilityEvent:
                    self.request_refresh(event_type)

        if event == event_processing_data.last_event:
            _LOGGER.debug("Event is the same! Skipping (%s)", event)
            return False

        event_processing_data.last_event = event
        if event_processing_data.subscriber_callbacks:
            _LOGGER.debug("Notify subscribers with %s", event)
            for callback in event_processing_data.subscriber_callbacks:
                create_task(self._tasks, callback(event))
            return True

        _LOGGER.debug("No subscribers... Discharging %s", event)
        return False

    def request_refresh(self, event_class: type[T]) -> None:
        """Request manual refresh."""
        if self.has_subscribers(event_class):
            create_task(self._tasks, self._call_refresh_function(event_class))

    async def teardown(self) -> None:
        """Teardown eventbus."""
        await cancel(self._tasks)

    async def _call_refresh_function(self, event_class: type[T]) -> None:
        semaphore = self._event_processing_dict[event_class].semaphore
        if semaphore.locked():
            _LOGGER.debug("Already refresh function running. Skipping...")
            return

        async with semaphore:
            from deebot_client.events.const import (  # pylint: disable=import-outside-toplevel
                EVENT_DTO_REFRESH_COMMANDS,
            )

            commands = EVENT_DTO_REFRESH_COMMANDS.get(event_class, [])
            if not commands:
                return

            if len(commands) == 1:
                await self._execute_command(commands[0])
            else:
                async with asyncio.TaskGroup() as tg:
                    for command in commands:
                        tg.create_task(self._execute_command(command))

    def _get_or_create_event_processing_data(
        self, event_class: type[T]
    ) -> _EventProcessingData[T]:
        with self._lock:
            event_processing_data = self._event_processing_dict.get(event_class, None)

            if event_processing_data is None:
                event_processing_data = _EventProcessingData()
                self._event_processing_dict[event_class] = event_processing_data

            return event_processing_data

    def get_last_event(
        self,
        event_type: type[T],
    ) -> T | None:
        """Get last event of type T, if available."""
        if event_processing := self._event_processing_dict.get(event_type, None):
            return event_processing.last_event

        return None
