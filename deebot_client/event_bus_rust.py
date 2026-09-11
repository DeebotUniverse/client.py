"""Event emitter module using Rust backend."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Final, TypeVar

from .events import AvailabilityEvent, Event, StateEvent
from .logging_filter import get_logger
from .models import State
from .util import cancel, create_task

try:
    from .rs.event_bus import EventBus as RustEventBus
except ImportError:
    # Fallback: Rust module not available
    RustEventBus = None  # type: ignore[assignment, misc]

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from .capabilities import Capabilities
    from .command import Command
    from .device import DeviceCommandExecute

_LOGGER = get_logger(__name__)

T = TypeVar("T", bound=Event)


def _get_event_type_id(event_type: type[Event]) -> int:
    """Get a unique ID for an event type."""
    return hash(event_type.__module__ + "." + event_type.__qualname__)


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


class _EventProcessingData[E: Event]:
    """Data class, which holds all needed data per EventDto."""

    def __init__(self, refresh_commands: list[Command]) -> None:
        self.refresh_commands: Final = refresh_commands

        self.subscriber_callbacks: Final[
            list[Callable[[E], Coroutine[Any, Any, None]]]
        ] = []
        self.notify_handle: asyncio.TimerHandle | None = None
        self.on_subscription_callbacks: Final[list[_OnSubscriptionCallback]] = []


class EventBus:
    """A very simple event bus system with Rust backend."""

    def __init__(
        self,
        execute_command: DeviceCommandExecute,
        capabilities: Capabilities,
    ) -> None:
        # Rust backend for state management
        if RustEventBus is None:
            raise ImportError(
                "Rust backend not available. Please build the Rust extension with "
                "'maturin develop' or use the Python implementation from "
                "deebot_client.event_bus"
            )

        self._rust_bus: Final = RustEventBus()

        # Python-side data structures for callbacks and commands
        self._event_processing_dict: dict[type[Event], _EventProcessingData[Any]] = {}
        self._tasks: set[asyncio.Future[Any]] = set()

        self._execute_command: Final = execute_command
        self._capabilities = capabilities

    @property
    def capabilities(self) -> Capabilities:
        """Return capabilities."""
        return self._capabilities

    def has_subscribers(self, event: type[T]) -> bool:
        """Return True, if emitter has subscribers."""
        event_id = _get_event_type_id(event)
        return self._rust_bus.has_subscribers(event_id)

    def subscribe(
        self,
        event_type: type[T],
        callback: Callable[[T], Coroutine[Any, Any, None]],
    ) -> Callable[[], None]:
        """Subscribe to event."""
        event_id = _get_event_type_id(event_type)
        event_processing_data = self._get_or_create_event_processing_data(event_type)

        def unsubscribe() -> None:
            event_processing_data.subscriber_callbacks.remove(callback)
            is_last = self._rust_bus.remove_subscriber(event_id)
            if is_last:
                for _callback in event_processing_data.on_subscription_callbacks:
                    _callback.unsubscribe()

        event_processing_data.subscriber_callbacks.append(callback)
        is_first, had_last_event = self._rust_bus.add_subscriber(event_id)

        if had_last_event:
            # Notify subscriber directly with the last event
            last_event = self._rust_bus.get_last_event(event_id)
            if last_event is not None:
                create_task(self._tasks, callback(last_event))
        elif is_first:
            # first subscriber therefore do refresh
            self.request_refresh(event_type)
            _LOGGER.debug("Calling on_first_subscription callbacks for %s", event_type)
            for _callback in event_processing_data.on_subscription_callbacks:
                create_task(self._tasks, _callback.call())

        return unsubscribe

    def notify(self, event: T, *, debounce_time: float = 0) -> None:  # noqa: C901
        """Notify subscriber with given event representation."""
        event_type = type(event)
        event_id = _get_event_type_id(event_type)
        event_processing_data = self._get_or_create_event_processing_data(event_type)

        # Cancel any pending notification
        if (
            handle := event_processing_data.notify_handle
        ) is not None and not handle.cancelled():
            handle.cancel()

        def _notify(event: T) -> None:  # noqa: PLR0912
            event_processing_data.notify_handle = None

            # Special handling for StateEvent
            if isinstance(event, StateEvent) and event.state == State.IDLE:
                last_event = self._rust_bus.get_last_event(event_id)
                if (
                    last_event is not None
                    and isinstance(last_event, StateEvent)
                    and last_event.state == State.DOCKED
                ):
                    # TODO distinguish better between docked and idle and outside event bus.
                    # Problem getCleanInfo will return state=idle, when bot is charging
                    event = StateEvent(State.DOCKED)  # type: ignore[assignment]

            # Special handling for AvailabilityEvent
            if isinstance(event, AvailabilityEvent) and event.available:
                last_event = self._rust_bus.get_last_event(event_id)
                if (
                    last_event is not None
                    and isinstance(last_event, AvailabilityEvent)
                    and not last_event.available
                ):
                    # unavailable -> available: refresh everything
                    for (
                        subscribed_event_id
                    ) in self._rust_bus.get_subscribed_event_types():
                        # Find the event type from our dict
                        for evt_type in self._event_processing_dict:
                            if _get_event_type_id(evt_type) == subscribed_event_id:
                                if evt_type != AvailabilityEvent:
                                    self.request_refresh(evt_type)
                                break

            # Check if notification should proceed (not a duplicate)
            debounce_ms = max(0, int(debounce_time * 1000))
            _should_notify, should_debounce, is_duplicate = (
                self._rust_bus.should_notify(event_id, event, debounce_ms)
            )

            if is_duplicate:
                _LOGGER.debug("Event is the same! Skipping (%s)", event)
                return

            if should_debounce:
                # Schedule for later
                self._rust_bus.set_pending_notification(event_id, True)
                event_processing_data.notify_handle = (
                    asyncio.get_running_loop().call_later(debounce_time, _notify, event)
                )
                return

            # Store the event in Rust backend
            self._rust_bus.store_event(event_id, event)

            if event_processing_data.subscriber_callbacks:
                _LOGGER.debug("Notify subscribers with %s", event)
                for callback in event_processing_data.subscriber_callbacks:
                    create_task(self._tasks, callback(event))
            else:
                _LOGGER.debug("No subscribers... Discharging %s", event)

        _notify(event)

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
        self._rust_bus.clear()

    async def _call_refresh_function(self, event_class: type[T]) -> None:
        event_id = _get_event_type_id(event_class)
        processing_data = self._event_processing_dict[event_class]

        # Try to acquire lock
        if not self._rust_bus.try_acquire_refresh_lock(event_id):
            _LOGGER.debug(
                "Already refresh function running for %s. Skipping...",
                event_class.__name__,
            )
            return

        try:
            commands = processing_data.refresh_commands
            if not commands:
                return

            if len(commands) == 1:
                await self._execute_command(commands[0])
            else:
                async with asyncio.TaskGroup() as tg:
                    for command in commands:
                        tg.create_task(self._execute_command(command))
        finally:
            self._rust_bus.release_refresh_lock(event_id)

    def _get_or_create_event_processing_data(
        self, event_class: type[T]
    ) -> _EventProcessingData[T]:
        # Python's GIL protects dict.get() and dict.__setitem__() as atomic operations
        # So we don't need a lock here - at worst we create the object twice
        event_processing_data = self._event_processing_dict.get(event_class, None)

        if event_processing_data is None:
            event_processing_data = _EventProcessingData(
                self._capabilities.get_refresh_commands(event_class)
            )
            # Use setdefault to handle race condition - only one will "win"
            event_processing_data = self._event_processing_dict.setdefault(
                event_class, event_processing_data
            )

        return event_processing_data

    def get_last_event(
        self,
        event_type: type[T],
    ) -> T | None:
        """Get last event of type T, if available."""
        event_id = _get_event_type_id(event_type)
        return self._rust_bus.get_last_event(event_id)

    def add_on_subscription_callback(
        self,
        event_type: type[T],
        callback: Callable[[], Coroutine[Any, Any, Callable[[], None]]],
    ) -> Callable[[], None]:
        """Add callback, which is called on the first subscription of the given event and the returned callable is called after the last subscriber has unsubscribed."""
        event_id = _get_event_type_id(event_type)
        event_processing_data = self._get_or_create_event_processing_data(event_type)

        data = _OnSubscriptionCallback(callback)

        def unsubscribe() -> None:
            data.unsubscribe()
            event_processing_data.on_subscription_callbacks.remove(data)
            self._rust_bus.remove_on_subscription_callback(event_id)

        event_processing_data.on_subscription_callbacks.append(data)
        self._rust_bus.add_on_subscription_callback(event_id)

        if self.has_subscribers(event_type):
            # There are already subscribers
            create_task(self._tasks, data.call())

        return unsubscribe
