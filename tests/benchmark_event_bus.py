"""Simple benchmark to compare Python vs Rust EventBus performance."""

from __future__ import annotations

import asyncio
import time
from typing import Any

# Import both implementations for comparison
from deebot_client.event_bus import EventBus as PythonEventBus
from deebot_client.event_bus_wrapper import EventBus as WrapperEventBus
from deebot_client.events import BatteryEvent


async def dummy_callback(event: BatteryEvent) -> None:
    """Dummy callback for testing."""
    pass


def dummy_execute_command(command: Any) -> None:
    """Dummy command executor."""
    pass


def dummy_get_refresh_commands(event_type: type) -> list:
    """Dummy refresh commands getter."""
    return []


def benchmark_event_bus(event_bus_class, name: str, iterations: int = 1000) -> float:
    """Benchmark an EventBus implementation."""
    print(f"\nBenchmarking {name}...")
    
    # Initialize
    event_bus = event_bus_class(dummy_execute_command, dummy_get_refresh_commands)
    
    # Subscribe some callbacks
    for i in range(10):
        event_bus.subscribe(BatteryEvent, dummy_callback)
    
    # Benchmark notification
    start_time = time.time()
    
    for i in range(iterations):
        event = BatteryEvent(i % 100)
        event_bus.notify(event)
        
        # Check has_subscribers occasionally
        if i % 100 == 0:
            event_bus.has_subscribers(BatteryEvent)
            
        # Get last event occasionally
        if i % 50 == 0:
            event_bus.get_last_event(BatteryEvent)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    print(f"{name}: {elapsed:.4f} seconds for {iterations} operations")
    print(f"{name}: {iterations/elapsed:.2f} operations per second")
    
    return elapsed


def main():
    """Run the benchmark."""
    print("EventBus Performance Benchmark")
    print("=" * 40)
    
    iterations = 10000
    
    # Benchmark Python implementation
    python_time = benchmark_event_bus(PythonEventBus, "Python EventBus", iterations)
    
    # Benchmark wrapper (will use Rust or fallback to Python)
    wrapper_time = benchmark_event_bus(WrapperEventBus, "Wrapper EventBus", iterations)
    
    # Check what implementation the wrapper is using
    wrapper_bus = WrapperEventBus(dummy_execute_command, dummy_get_refresh_commands)
    if hasattr(wrapper_bus, 'is_rust_implementation'):
        using_rust = wrapper_bus.is_rust_implementation
        impl_type = "Rust" if using_rust else "Python fallback"
        print(f"\nWrapper is using: {impl_type}")
        
        if using_rust and wrapper_time < python_time:
            speedup = python_time / wrapper_time
            print(f"Rust implementation is {speedup:.2f}x faster!")
        elif not using_rust:
            print("Rust implementation not available, using Python fallback")
    
    print(f"\nBenchmark complete.")


if __name__ == "__main__":
    main()