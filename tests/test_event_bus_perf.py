"""Performance tests for event bus implementations."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from deebot_client.event_bus import EventBus as PythonEventBus
from deebot_client.events import BatteryEvent, StateEvent

try:
    from deebot_client.event_bus_rust import EventBus as RustEventBus

    RUST_AVAILABLE = True
except ImportError:
    RustEventBus = None  # type: ignore[misc, assignment]
    RUST_AVAILABLE = False

if TYPE_CHECKING:
    from pytest_codspeed import BenchmarkFixture

    from deebot_client.event_bus import EventBus


@pytest.fixture(
    params=["python"] + (["rust"] if RUST_AVAILABLE else [])
)
def event_bus_impl(request: pytest.FixtureRequest, execute_mock: AsyncMock) -> EventBus:
    """Fixture that provides both Python and Rust implementations."""
    from tests.conftest import get_capabilities

    capabilities = get_capabilities()
    if request.param == "python":
        return PythonEventBus(execute_mock, capabilities)
    if RustEventBus is None:
        pytest.skip("Rust backend not available")
    return RustEventBus(execute_mock, capabilities)


@pytest.mark.benchmark
def test_subscribe_unsubscribe(
    benchmark: BenchmarkFixture, event_bus_impl: EventBus
) -> None:
    """Benchmark subscribing and unsubscribing to events."""

    def subscribe_unsubscribe() -> None:
        unsubscribe = event_bus_impl.subscribe(BatteryEvent, AsyncMock())
        unsubscribe()

    benchmark(subscribe_unsubscribe)


@pytest.mark.benchmark
def test_multiple_subscriptions(
    benchmark: BenchmarkFixture, event_bus_impl: EventBus
) -> None:
    """Benchmark multiple subscriptions to the same event."""

    def multiple_subscriptions() -> None:
        unsubscribers = []
        for _ in range(10):
            unsubscribe = event_bus_impl.subscribe(BatteryEvent, AsyncMock())
            unsubscribers.append(unsubscribe)

        for unsubscribe in unsubscribers:
            unsubscribe()

    benchmark(multiple_subscriptions)


@pytest.mark.benchmark
def test_notify_no_subscribers(
    benchmark: BenchmarkFixture, event_bus_impl: EventBus
) -> None:
    """Benchmark notifying when there are no subscribers."""

    def notify() -> None:
        event_bus_impl.notify(BatteryEvent(50))

    benchmark(notify)


@pytest.mark.benchmark
def test_notify_with_subscribers(
    benchmark: BenchmarkFixture, event_bus_impl: EventBus
) -> None:
    """Benchmark notifying with subscribers."""
    # Setup: subscribe before benchmark
    event_bus_impl.subscribe(BatteryEvent, AsyncMock())

    def notify() -> None:
        event_bus_impl.notify(BatteryEvent(50))

    benchmark(notify)


@pytest.mark.benchmark
def test_notify_duplicate_event(
    benchmark: BenchmarkFixture, event_bus_impl: EventBus
) -> None:
    """Benchmark duplicate event detection."""
    event_bus_impl.subscribe(BatteryEvent, AsyncMock())
    # First notification
    event_bus_impl.notify(BatteryEvent(50))

    def notify_duplicate() -> None:
        # This should be detected as duplicate
        event_bus_impl.notify(BatteryEvent(50))

    benchmark(notify_duplicate)


@pytest.mark.benchmark
def test_has_subscribers(benchmark: BenchmarkFixture, event_bus_impl: EventBus) -> None:
    """Benchmark checking for subscribers."""
    event_bus_impl.subscribe(BatteryEvent, AsyncMock())

    def has_subscribers() -> None:
        event_bus_impl.has_subscribers(BatteryEvent)

    benchmark(has_subscribers)


@pytest.mark.benchmark
def test_get_last_event(benchmark: BenchmarkFixture, event_bus_impl: EventBus) -> None:
    """Benchmark retrieving the last event."""
    event_bus_impl.notify(BatteryEvent(75))

    def get_last_event() -> None:
        event_bus_impl.get_last_event(BatteryEvent)

    benchmark(get_last_event)


@pytest.mark.benchmark
def test_notify_different_events(
    benchmark: BenchmarkFixture, event_bus_impl: EventBus
) -> None:
    """Benchmark notifying different event types."""
    event_bus_impl.subscribe(BatteryEvent, AsyncMock())
    event_bus_impl.subscribe(StateEvent, AsyncMock())

    def notify_different() -> None:
        event_bus_impl.notify(BatteryEvent(50))
        event_bus_impl.notify(StateEvent.from_state("STATE_CLEANING"))

    benchmark(notify_different)


@pytest.mark.benchmark
def test_concurrent_operations(
    benchmark: BenchmarkFixture, event_bus_impl: EventBus
) -> None:
    """Benchmark concurrent subscribe/notify operations."""

    def concurrent_ops() -> None:
        # Subscribe
        unsubscribers = []
        for i in range(5):
            unsubscribers.append(event_bus_impl.subscribe(BatteryEvent, AsyncMock()))

        # Notify
        for i in range(10):
            event_bus_impl.notify(BatteryEvent(i * 10))

        # Unsubscribe
        for unsubscribe in unsubscribers:
            unsubscribe()

    benchmark(concurrent_ops)


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_async_notify_with_callbacks(
    benchmark: BenchmarkFixture, event_bus_impl: EventBus
) -> None:
    """Benchmark async notification with actual callback execution."""
    callback_count = 0

    async def callback(event: BatteryEvent) -> None:
        nonlocal callback_count
        callback_count += 1
        await asyncio.sleep(0)  # Yield control

    event_bus_impl.subscribe(BatteryEvent, callback)

    async def notify_and_wait() -> None:
        for i in range(10):
            event_bus_impl.notify(BatteryEvent(i * 10))
        # Wait for callbacks to execute
        await asyncio.sleep(0.1)

    await benchmark.async_func(notify_and_wait)
    assert callback_count > 0


@pytest.mark.benchmark
def test_debounce_check(benchmark: BenchmarkFixture, event_bus_impl: EventBus) -> None:
    """Benchmark debouncing logic."""
    event_bus_impl.subscribe(BatteryEvent, AsyncMock())

    def notify_with_debounce() -> None:
        # Notify with debouncing
        event_bus_impl.notify(BatteryEvent(50), debounce_time=1.0)

    benchmark(notify_with_debounce)


# Rust-only benchmarks to test Rust-specific optimizations
@pytest.mark.benchmark
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust backend not available")
def test_rust_state_management(benchmark: BenchmarkFixture, execute_mock: AsyncMock) -> None:
    """Benchmark Rust state management operations."""
    from tests.conftest import get_capabilities

    capabilities = get_capabilities()
    if RustEventBus is None:
        pytest.skip("Rust backend not available")
    rust_bus = RustEventBus(execute_mock, capabilities)

    def state_operations() -> None:
        # Subscribe
        rust_bus.subscribe(BatteryEvent, AsyncMock())
        # Notify
        rust_bus.notify(BatteryEvent(50))
        # Check subscribers
        rust_bus.has_subscribers(BatteryEvent)
        # Get last event
        rust_bus.get_last_event(BatteryEvent)

    benchmark(state_operations)


@pytest.mark.benchmark
def test_python_state_management(benchmark: BenchmarkFixture, execute_mock: AsyncMock) -> None:
    """Benchmark Python state management operations."""
    from tests.conftest import get_capabilities

    capabilities = get_capabilities()
    python_bus = PythonEventBus(execute_mock, capabilities)

    def state_operations() -> None:
        # Subscribe
        python_bus.subscribe(BatteryEvent, AsyncMock())
        # Notify
        python_bus.notify(BatteryEvent(50))
        # Check subscribers
        python_bus.has_subscribers(BatteryEvent)
        # Get last event
        python_bus.get_last_event(BatteryEvent)

    benchmark(state_operations)
