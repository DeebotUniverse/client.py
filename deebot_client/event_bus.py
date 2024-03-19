"""Event emitter module."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import threading
from typing import TYPE_CHECKING, Any, Final, Generic, TypeVar

from .events import AvailabilityEvent, Event, StateEvent
from .logging_filter import get_logger
from .models import State
from .util import cancel, create_task

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from .command import Command

_LOGGER = get_logger(__name__)

T = TypeVar("T", bound=Event)


class _OnSubscriptionCallback:
    def __init__(
        self, callback: Callable[[], Coroutine[Any, Any, Callable[[], None]]]
    ) -> None:
        """Init."""
        self._callback = callback
        self._unsub: Callable[[], None] | None = None

    async def call(self) -> None:
        """Execute callback."""
        if not self._unsub:
            self._unsub = await self._callback()

    def unsubscribe(self) -> None:
        """Execute unsubscribe."""
        if self._unsub:
            self._unsub()
            self._unsub = None


class _EventProcessingData(Generic[T]):
    """Data class, which holds all needed data per EventDto."""

    def __init__(self, refresh_commands: list[Command]) -> None:
        self.refresh_commands: Final = refresh_commands

        self.subscriber_callbacks: Final[
            list[Callable[[T], Coroutine[Any, Any, None]]]
        ] = []
        self.semaphore: Final = asyncio.Semaphore(1)
        self.last_event: T | None = None
        self.last_event_time: datetime = datetime(1, 1, 1, 1, 1, 1, tzinfo=UTC)
        self.notify_handle: asyncio.TimerHandle | None = None
        self.on_subscription_callbacks: Final[list[_OnSubscriptionCallback]] = []


class EventBus:
    """A very simple event bus system."""

    def __init__(
        self,
        execute_command: Callable[[Command], Coroutine[Any, Any, None]],
        get_refresh_commands: Callable[[type[Event]], list[Command]],
    ) -> None:
        self._event_processing_dict: dict[type[Event], _EventProcessingData[Any]] = {}
        self._lock = threading.Lock()
        self._tasks: set[asyncio.Future[Any]] = set()

        self._execute_command: Final = execute_command
        self._get_refresh_commands = get_refresh_commands

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
            if not event_processing_data.subscriber_callbacks:
                for _callback in event_processing_data.on_subscription_callbacks:
                    _callback.unsubscribe()

        event_processing_data.subscriber_callbacks.append(callback)

        if event_processing_data.last_event:
            # Notify subscriber directly with the last event
            create_task(self._tasks, callback(event_processing_data.last_event))
        elif len(event_processing_data.subscriber_callbacks) == 1:
            # first subscriber therefore do refresh
            self.request_refresh(event_type)
            _LOGGER.debug("Calling on_first_subscription callbacks for %s", event_type)
            for _callback in event_processing_data.on_subscription_callbacks:
                create_task(self._tasks, _callback.call())

        return unsubscribe

    def notify(self, event: T, *, debounce_time: float = 0) -> None:
        """Notify subscriber with given event representation."""
        event_processing_data = self._get_or_create_event_processing_data(type(event))

        if (
            handle := event_processing_data.notify_handle
        ) is not None and not handle.cancelled():
            handle.cancel()

        def _notify(event: T) -> None:
            event_processing_data.last_event_time = datetime.now(UTC)
            event_processing_data.notify_handle = None

            if (
                isinstance(event, StateEvent)
                and event.state == State.IDLE
                and event_processing_data.last_event
                and event_processing_data.last_event.state == State.DOCKED  # type: ignore[attr-defined]
            ):
                # TODO distinguish better between docked and idle and outside event bus. # pylint: disable=fixme
                # Problem getCleanInfo will return state=idle, when bot is charging
                event = StateEvent(State.DOCKED)  # type: ignore[assignment]
            elif (
                isinstance(event, AvailabilityEvent)
                and event.available
                and event_processing_data.last_event
                and not event_processing_data.last_event.available  # type: ignore[attr-defined]
            ):
                # unavailable -> available: refresh everything
                for event_type in self._event_processing_dict:
                    if event_type != AvailabilityEvent:
                        self.request_refresh(event_type)

            if event == event_processing_data.last_event:
                _LOGGER.debug("Event is the same! Skipping (%s)", event)
                return

            event_processing_data.last_event = event
            if event_processing_data.subscriber_callbacks:
                _LOGGER.debug("Notify subscribers with %s", event)
                for callback in event_processing_data.subscriber_callbacks:
                    create_task(self._tasks, callback(event))
            else:
                _LOGGER.debug("No subscribers... Discharging %s", event)

        now = datetime.now(UTC)
        if debounce_time <= 0 or (
            now - event_processing_data.last_event_time
        ) > timedelta(seconds=debounce_time):
            _notify(event)
        else:
            event_processing_data.notify_handle = asyncio.get_running_loop().call_later(
                debounce_time, _notify, event
            )

    def request_refresh(self, event_class: type[T]) -> None:
        """Request manual refresh."""
        if self.has_subscribers(event_class):
            create_task(self._tasks, self._call_refresh_function(event_class))

    async def teardown(self) -> None:
        """Teardown eventbus."""
        await cancel(self._tasks)
        for data in self._event_processing_dict.values():
            if handle := data.notify_handle:
                handle.cancel()

    async def _call_refresh_function(self, event_class: type[T]) -> None:
        processing_data = self._event_processing_dict[event_class]
        semaphore = processing_data.semaphore
        if semaphore.locked():
            _LOGGER.debug(
                "Already refresh function running for %s. Skipping...",
                event_class.__name__,
            )
            return

        async with semaphore:
            commands = processing_data.refresh_commands
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
                event_processing_data = _EventProcessingData(
                    self._get_refresh_commands(event_class)
                )
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

    def add_on_subscription_callback(
        self,
        event_type: type[T],
        callback: Callable[[], Coroutine[Any, Any, Callable[[], None]]],
    ) -> Callable[[], None]:
        """Add callback, which is called on the first subscription of the given event and the returned callable is called after the last subscriber has unsubscribed."""
        event_processing_data = self._get_or_create_event_processing_data(event_type)

        data = _OnSubscriptionCallback(callback)

        def unsubscribe() -> None:
            data.unsubscribe()
            event_processing_data.on_subscription_callbacks.remove(data)

        event_processing_data.on_subscription_callbacks.append(data)

        if self.has_subscribers(event_type):
            # There are already subscribers
            create_task(self._tasks, data.call())

        return unsubscribe
