"""Rust EventBus type stubs."""

from __future__ import annotations

from typing import Any, Callable, Coroutine, TypeVar
from collections.abc import Awaitable

from ..events.base import Event

__all__ = ["EventBus"]

T = TypeVar("T", bound=Event)

class EventBus:
    """High-performance Rust-based EventBus using Tokio."""
    
    def __init__(
        self,
        execute_command: Callable[[Any], Coroutine[Any, Any, None]],
        get_refresh_commands: Callable[[type[Event]], list[Any]],
    ) -> None: ...
    
    def has_subscribers(self, event_type: type[T]) -> bool:
        """Check if there are subscribers for an event type."""
        ...
    
    def subscribe(
        self,
        event_type: type[T],
        callback: Callable[[T], Coroutine[Any, Any, None]],
    ) -> Callable[[], None]:
        """Subscribe to an event type with a callback."""
        ...
    
    def notify(self, event: T, *, debounce_time: float = 0) -> None:
        """Notify subscribers with an event, optionally with debouncing."""
        ...
    
    def request_refresh(self, event_type: type[T]) -> None:
        """Request manual refresh for an event type."""
        ...
    
    def get_last_event(self, event_type: type[T]) -> T | None:
        """Get the last event for an event type."""
        ...
    
    def add_on_subscription_callback(
        self,
        event_type: type[T],
        callback: Callable[[], Coroutine[Any, Any, Callable[[], None]]],
    ) -> Callable[[], None]:
        """Add a callback that's called on first subscription."""
        ...
    
    async def teardown(self) -> None:
        """Teardown the event bus, cancelling all tasks and handles."""
        ...