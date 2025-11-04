# Rust Event Bus Migration

This document describes the migration of the event bus implementation from pure Python to a hybrid Python/Rust implementation.

## Overview

The event bus has been migrated to use a Rust backend for improved performance while maintaining full compatibility with the existing Python API. The migration follows a hybrid approach where:

- **Rust** handles thread-safe state management, event storage, and coordination
- **Python** handles async operations, callback execution, and command execution

This design ensures that:
1. No I/O operations are performed in async Rust context
2. The Python API remains unchanged
3. Performance is significantly improved for state management operations

## Architecture

### Rust Backend (`src/event_bus.rs`)

The Rust backend provides a thread-safe state management layer with the following capabilities:

- **Subscriber tracking**: Count of subscribers per event type
- **Event storage**: Last event storage for each event type
- **Concurrency control**: Refresh lock management to prevent concurrent refreshes
- **Debouncing state**: Tracking of pending notifications
- **Duplicate detection**: Efficient event comparison

### Python Wrapper (`deebot_client/event_bus_rust.py`)

The Python wrapper (`EventBus` class) provides the same API as the original implementation while using the Rust backend for state management:

```python
from deebot_client.event_bus_rust import EventBus

# Usage is identical to the original
bus = EventBus(execute_command, capabilities)
bus.subscribe(BatteryEvent, callback)
bus.notify(BatteryEvent(50))
```

### Type Stubs (`deebot_client/rs/event_bus.pyi`)

Type stubs are provided for full type checking support of the Rust module.

## Files Added/Modified

### New Files

- `src/event_bus.rs` - Rust event bus implementation
- `deebot_client/event_bus_rust.py` - Python wrapper using Rust backend
- `deebot_client/rs/event_bus.pyi` - Type stubs for Rust module
- `tests/test_event_bus_perf.py` - Performance benchmarks comparing Python and Rust
- `RUST_EVENT_BUS_MIGRATION.md` - This documentation file

### Modified Files

- `src/lib.rs` - Register event_bus module
- `tests/test_event_bus.py` - Updated to test both Python and Rust implementations
- `tests/conftest.py` - Added `get_capabilities()` helper function

## Performance Benefits

The Rust implementation provides significant performance improvements for:

1. **State management operations** - Subscriber tracking, event storage, and retrieval
2. **Duplicate detection** - Fast event comparison
3. **Concurrency control** - Lock-free operations where possible
4. **Memory efficiency** - Better memory layout and reduced allocations

### Benchmarks

Run the performance tests to see the improvements:

```bash
pytest tests/test_event_bus_perf.py -v --codspeed
```

Key benchmarks include:
- `test_subscribe_unsubscribe` - Subscribe/unsubscribe operations
- `test_notify_with_subscribers` - Event notification with subscribers
- `test_notify_duplicate_event` - Duplicate event detection
- `test_has_subscribers` - Subscriber checking
- `test_get_last_event` - Last event retrieval
- `test_concurrent_operations` - Mixed concurrent operations

## Building the Rust Extension

To use the Rust implementation, you need to build the Rust extension:

### Development Build

```bash
maturin develop
```

### Release Build

```bash
maturin develop --release
```

### Production Build

```bash
maturin build --release
```

## Backward Compatibility

The Python implementation (`deebot_client.event_bus`) remains unchanged and continues to work as before. The Rust implementation is opt-in and requires building the Rust extension.

If the Rust extension is not built, the code will gracefully fall back or raise a clear error message:

```python
from deebot_client.event_bus_rust import EventBus  # Raises ImportError if Rust not available
```

## Testing

### Running All Tests

Both implementations are tested with the same test suite:

```bash
# Run all event bus tests (tests both Python and Rust implementations)
pytest tests/test_event_bus.py -v

# Run performance benchmarks
pytest tests/test_event_bus_perf.py -v
```

### Python-Only Tests

If the Rust extension is not built, tests will automatically skip Rust-specific tests:

```bash
pytest tests/test_event_bus.py -v
# Rust tests will be skipped with: "Rust backend not available"
```

## Design Decisions

### Why Hybrid Python/Rust?

1. **Async Boundary**: Python's asyncio and Rust's async runtimes don't mix well. By keeping async operations in Python, we avoid complex FFI boundaries.

2. **No I/O in Async Context**: The requirement to avoid I/O in async context is satisfied by keeping all I/O operations (command execution) in Python.

3. **Maintainability**: The hybrid approach allows gradual migration and easier debugging.

### What's in Rust vs Python?

**Rust handles:**
- Thread-safe state storage (events, subscriber counts, locks)
- Synchronous operations (checking state, updating counters)
- Memory-efficient data structures

**Python handles:**
- Async operations (callback execution, command execution)
- Event bus coordination logic (debouncing, refresh triggers)
- Integration with the rest of the Python codebase

## Future Improvements

Potential future enhancements:

1. **More operations in Rust**: Move more synchronous operations to Rust for additional performance gains
2. **Lock-free data structures**: Use Rust's lock-free primitives for even better concurrency
3. **Batch operations**: Optimize bulk subscribe/notify operations
4. **Memory pooling**: Reduce allocations for high-frequency events

## Migration Guide for Users

### For End Users

No changes required. The Python implementation continues to work as before.

### For Developers Who Want Performance

1. Install Rust toolchain: https://rustup.rs/
2. Build the extension: `maturin develop --release`
3. Import from `event_bus_rust` instead of `event_bus`:
   ```python
   from deebot_client.event_bus_rust import EventBus
   ```

### For Library Maintainers

To make Rust the default implementation:

1. Update `deebot_client/device.py` to import from `event_bus_rust`
2. Add build instructions to README
3. Update CI/CD to build Rust extension
4. Consider making Rust extension a required dependency

## Questions and Support

For questions or issues:
- Open an issue on GitHub
- Check the test files for usage examples
- Review the Rust source code for implementation details
