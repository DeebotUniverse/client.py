"""Type stubs for the Rust event_bus module."""

from typing import Any

class EventBus:
    """Rust-based event bus for managing event state and subscriptions.

    This class handles thread-safe state management for events including:
    - Subscriber tracking
    - Last event storage
    - Refresh lock management
    - Debouncing state
    """

    def __init__(self) -> None:
        """Initialize the event bus."""
    def has_subscribers(self, event_type_id: int) -> bool:
        """Check if an event type has subscribers.

        Args:
            event_type_id: The unique identifier for the event type

        Returns:
            True if the event type has subscribers

        """
    def add_subscriber(self, event_type_id: int) -> tuple[bool, bool]:
        """Add a subscriber to an event type.

        Args:
            event_type_id: The unique identifier for the event type

        Returns:
            A tuple of (is_first_subscriber, had_last_event)

        """
    def remove_subscriber(self, event_type_id: int) -> bool:
        """Remove a subscriber from an event type.

        Args:
            event_type_id: The unique identifier for the event type

        Returns:
            True if this was the last subscriber

        """
    def get_last_event(self, event_type_id: int) -> Any | None:
        """Get the last event for an event type.

        Args:
            event_type_id: The unique identifier for the event type

        Returns:
            The last event object or None if no event has been stored

        """
    def should_notify(
        self,
        event_type_id: int,
        event: Any,
        debounce_time_ms: int,
    ) -> tuple[bool, bool, bool]:
        """Check if we should notify subscribers.

        Args:
            event_type_id: The unique identifier for the event type
            event: The event object to check
            debounce_time_ms: Debounce time in milliseconds

        Returns:
            A tuple of (should_notify, should_debounce, is_duplicate)

        """
    def store_event(self, event_type_id: int, event: Any) -> None:
        """Store an event after notification.

        Args:
            event_type_id: The unique identifier for the event type
            event: The event object to store

        """
    def set_pending_notification(self, event_type_id: int, pending: bool) -> None:
        """Mark that a debounced notification is pending.

        Args:
            event_type_id: The unique identifier for the event type
            pending: Whether a notification is pending

        """
    def has_pending_notification(self, event_type_id: int) -> bool:
        """Check if there's a pending notification.

        Args:
            event_type_id: The unique identifier for the event type

        Returns:
            True if there's a pending notification

        """
    def try_acquire_refresh_lock(self, event_type_id: int) -> bool:
        """Try to acquire refresh lock.

        Args:
            event_type_id: The unique identifier for the event type

        Returns:
            True if lock was acquired

        """
    def release_refresh_lock(self, event_type_id: int) -> None:
        """Release refresh lock.

        Args:
            event_type_id: The unique identifier for the event type

        """
    def get_subscribed_event_types(self) -> list[int]:
        """Get all event type IDs that have subscribers.

        Returns:
            A list of event type IDs

        """
    def add_on_subscription_callback(self, event_type_id: int) -> None:
        """Add on subscription callback.

        Args:
            event_type_id: The unique identifier for the event type

        """
    def remove_on_subscription_callback(self, event_type_id: int) -> None:
        """Remove on subscription callback.

        Args:
            event_type_id: The unique identifier for the event type

        """
    def clear(self) -> None:
        """Clear all data (for teardown)."""
