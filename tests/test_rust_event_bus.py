"""Tests for the Rust EventBus implementation."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from deebot_client.event_bus_wrapper import EventBus
from deebot_client.events import BatteryEvent, StateEvent


@pytest.fixture
def execute_mock():
    """Mock execute command function."""
    return AsyncMock()


@pytest.fixture
def get_refresh_commands_mock():
    """Mock get refresh commands function."""
    return lambda event_type: []


@pytest.fixture
def event_bus(execute_mock, get_refresh_commands_mock):
    """Create an EventBus instance for testing."""
    return EventBus(execute_mock, get_refresh_commands_mock)


def test_event_bus_initialization(event_bus):
    """Test that EventBus initializes correctly."""
    assert event_bus is not None
    # Test whether it's using Rust or Python implementation
    print(f"EventBus implementation: {event_bus}")


def test_has_subscribers_initially_false(event_bus):
    """Test that has_subscribers returns False initially."""
    assert not event_bus.has_subscribers(BatteryEvent)


def test_subscribe_returns_unsubscribe_function(event_bus):
    """Test that subscribe returns an unsubscribe function."""
    callback = AsyncMock()
    unsubscribe = event_bus.subscribe(BatteryEvent, callback)
    assert callable(unsubscribe)


def test_get_last_event_initially_none(event_bus):
    """Test that get_last_event returns None initially."""
    assert event_bus.get_last_event(BatteryEvent) is None


def test_notify_does_not_raise(event_bus):
    """Test that notify does not raise an exception."""
    event = BatteryEvent(100)
    event_bus.notify(event)  # Should not raise


def test_request_refresh_does_not_raise(event_bus):
    """Test that request_refresh does not raise an exception."""
    event_bus.request_refresh(BatteryEvent)  # Should not raise


async def test_teardown_is_awaitable(event_bus):
    """Test that teardown can be awaited."""
    await event_bus.teardown()  # Should not raise


def test_add_on_subscription_callback_returns_function(event_bus):
    """Test that add_on_subscription_callback returns a function."""
    async def callback():
        return lambda: None
    
    unsubscribe = event_bus.add_on_subscription_callback(BatteryEvent, callback)
    assert callable(unsubscribe)


def test_rust_implementation_property_exists(event_bus):
    """Test that the is_rust_implementation property exists."""
    assert hasattr(event_bus, 'is_rust_implementation')
    is_rust = event_bus.is_rust_implementation
    assert isinstance(is_rust, bool)
    print(f"Using Rust implementation: {is_rust}")


def test_wrapper_repr(event_bus):
    """Test that the wrapper has a meaningful repr."""
    repr_str = repr(event_bus)
    assert "EventBus" in repr_str
    assert ("Rust" in repr_str) or ("Python" in repr_str)