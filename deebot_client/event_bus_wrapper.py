"""EventBus wrapper with Rust fallback for performance."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Final, TypeVar

from .logging_filter import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from .command import Command
    from .device import DeviceCommandExecute
    from .events.base import Event

_LOGGER = get_logger(__name__)

T = TypeVar("T", bound="Event")

# Try to import Rust implementation, fall back to Python
_USE_RUST = False
try:
    from .rs.event_bus import EventBus as RustEventBus
    _USE_RUST = True
    _LOGGER.info("Using high-performance Rust EventBus implementation")
except ImportError:
    _LOGGER.info("Rust EventBus not available, falling back to Python implementation")
    from .event_bus import EventBus as PythonEventBus


class EventBus:
    """A high-performance event bus system with Rust backend when available."""

    def __init__(
        self,
        execute_command: DeviceCommandExecute,
        get_refresh_commands: Callable[[type[Event]], list[Command]],
    ) -> None:
        """Initialize EventBus with the best available implementation."""
        if _USE_RUST:
            self._impl = RustEventBus(execute_command, get_refresh_commands)
            self._is_rust = True
        else:
            self._impl = PythonEventBus(execute_command, get_refresh_commands)
            self._is_rust = False

    def has_subscribers(self, event: type[T]) -> bool:
        """Return True, if emitter has subscribers."""
        return self._impl.has_subscribers(event)

    def subscribe(
        self,
        event_type: type[T],
        callback: Callable[[T], Coroutine[Any, Any, None]],
    ) -> Callable[[], None]:
        """Subscribe to event."""
        return self._impl.subscribe(event_type, callback)

    def notify(self, event: T, *, debounce_time: float = 0) -> None:
        """Notify subscriber with given event representation."""
        return self._impl.notify(event, debounce_time=debounce_time)

    def request_refresh(self, event_class: type[T]) -> None:
        """Request manual refresh."""
        return self._impl.request_refresh(event_class)

    async def teardown(self) -> None:
        """Teardown eventbus."""
        return await self._impl.teardown()

    def get_last_event(
        self,
        event_type: type[T],
    ) -> T | None:
        """Get last event of type T, if available."""
        return self._impl.get_last_event(event_type)

    def add_on_subscription_callback(
        self,
        event_type: type[T],
        callback: Callable[[], Coroutine[Any, Any, Callable[[], None]]],
    ) -> Callable[[], None]:
        """Add callback, which is called on the first subscription of the given event and the returned callable is called after the last subscriber has unsubscribed."""
        return self._impl.add_on_subscription_callback(event_type, callback)

    @property
    def is_rust_implementation(self) -> bool:
        """Return True if using Rust implementation."""
        return self._is_rust

    def __repr__(self) -> str:
        impl_type = "Rust" if self._is_rust else "Python"
        return f"EventBus({impl_type} implementation)"