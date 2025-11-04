use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

/// Represents an event type identifier (hash of the Python type)
pub type EventTypeId = u64;

/// Data stored per event type
#[derive(Clone)]
struct EventProcessingData {
    /// Subscribers count (we don't store Python callbacks in Rust to avoid GIL issues)
    subscriber_count: usize,
    /// Last event data (as Python object)
    last_event: Option<PyObject>,
    /// Last event timestamp (milliseconds since epoch)
    last_event_time: u128,
    /// Whether a refresh is currently running
    refresh_locked: bool,
    /// Pending notification handle (for debouncing)
    has_pending_notification: bool,
    /// On subscription callbacks count
    on_subscription_callback_count: usize,
}

impl EventProcessingData {
    fn new() -> Self {
        Self {
            subscriber_count: 0,
            last_event: None,
            last_event_time: 0,
            refresh_locked: false,
            has_pending_notification: false,
            on_subscription_callback_count: 0,
        }
    }
}

/// The event bus implementation in Rust
/// This handles state management and coordination, while Python handles async operations
#[pyclass]
pub struct EventBus {
    data: Arc<Mutex<HashMap<EventTypeId, EventProcessingData>>>,
}

#[pymethods]
impl EventBus {
    #[new]
    fn new() -> Self {
        Self {
            data: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Check if an event type has subscribers
    fn has_subscribers(&self, event_type_id: EventTypeId) -> bool {
        let data = self.data.lock().unwrap();
        data.get(&event_type_id)
            .map(|d| d.subscriber_count > 0)
            .unwrap_or(false)
    }

    /// Add a subscriber to an event type
    /// Returns a tuple (is_first_subscriber, had_last_event)
    fn add_subscriber(&self, event_type_id: EventTypeId) -> (bool, bool) {
        let mut data = self.data.lock().unwrap();
        let entry = data.entry(event_type_id).or_insert_with(EventProcessingData::new);

        let was_empty = entry.subscriber_count == 0;
        entry.subscriber_count += 1;
        let had_last_event = entry.last_event.is_some();

        (was_empty, had_last_event)
    }

    /// Remove a subscriber from an event type
    /// Returns true if this was the last subscriber
    fn remove_subscriber(&self, event_type_id: EventTypeId) -> bool {
        let mut data = self.data.lock().unwrap();
        if let Some(entry) = data.get_mut(&event_type_id) {
            if entry.subscriber_count > 0 {
                entry.subscriber_count -= 1;
                return entry.subscriber_count == 0;
            }
        }
        false
    }

    /// Get the last event for an event type
    fn get_last_event(&self, event_type_id: EventTypeId, py: Python<'_>) -> Option<PyObject> {
        let data = self.data.lock().unwrap();
        data.get(&event_type_id)
            .and_then(|d| d.last_event.as_ref().map(|e| e.clone_ref(py)))
    }

    /// Check if we should notify subscribers
    /// Returns tuple (should_notify, should_debounce, is_duplicate)
    fn should_notify(
        &self,
        event_type_id: EventTypeId,
        event: PyObject,
        debounce_time_ms: u128,
        py: Python<'_>,
    ) -> (bool, bool, bool) {
        let mut data = self.data.lock().unwrap();
        let entry = data.entry(event_type_id).or_insert_with(EventProcessingData::new);

        // Check if event is duplicate
        let is_duplicate = if let Some(ref last_event) = entry.last_event {
            match event.bind(py).eq(last_event.bind(py)) {
                Ok(result) => result,
                Err(_) => false,
            }
        } else {
            false
        };

        if is_duplicate {
            return (false, false, true);
        }

        // Check if we need debouncing
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_millis();

        let time_since_last = now.saturating_sub(entry.last_event_time);
        let should_debounce = debounce_time_ms > 0 && time_since_last <= debounce_time_ms;

        (true, should_debounce, false)
    }

    /// Store an event after notification
    fn store_event(&self, event_type_id: EventTypeId, event: PyObject) {
        let mut data = self.data.lock().unwrap();
        let entry = data.entry(event_type_id).or_insert_with(EventProcessingData::new);

        entry.last_event = Some(event);
        entry.last_event_time = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_millis();
        entry.has_pending_notification = false;
    }

    /// Mark that a debounced notification is pending
    fn set_pending_notification(&self, event_type_id: EventTypeId, pending: bool) {
        let mut data = self.data.lock().unwrap();
        if let Some(entry) = data.get_mut(&event_type_id) {
            entry.has_pending_notification = pending;
        }
    }

    /// Check if there's a pending notification
    fn has_pending_notification(&self, event_type_id: EventTypeId) -> bool {
        let data = self.data.lock().unwrap();
        data.get(&event_type_id)
            .map(|d| d.has_pending_notification)
            .unwrap_or(false)
    }

    /// Try to acquire refresh lock
    /// Returns true if lock was acquired
    fn try_acquire_refresh_lock(&self, event_type_id: EventTypeId) -> bool {
        let mut data = self.data.lock().unwrap();
        let entry = data.entry(event_type_id).or_insert_with(EventProcessingData::new);

        if entry.refresh_locked {
            false
        } else {
            entry.refresh_locked = true;
            true
        }
    }

    /// Release refresh lock
    fn release_refresh_lock(&self, event_type_id: EventTypeId) {
        let mut data = self.data.lock().unwrap();
        if let Some(entry) = data.get_mut(&event_type_id) {
            entry.refresh_locked = false;
        }
    }

    /// Get all event type IDs that have subscribers
    fn get_subscribed_event_types(&self) -> Vec<EventTypeId> {
        let data = self.data.lock().unwrap();
        data.iter()
            .filter(|(_, d)| d.subscriber_count > 0)
            .map(|(id, _)| *id)
            .collect()
    }

    /// Add on subscription callback
    fn add_on_subscription_callback(&self, event_type_id: EventTypeId) {
        let mut data = self.data.lock().unwrap();
        let entry = data.entry(event_type_id).or_insert_with(EventProcessingData::new);
        entry.on_subscription_callback_count += 1;
    }

    /// Remove on subscription callback
    fn remove_on_subscription_callback(&self, event_type_id: EventTypeId) {
        let mut data = self.data.lock().unwrap();
        if let Some(entry) = data.get_mut(&event_type_id) {
            if entry.on_subscription_callback_count > 0 {
                entry.on_subscription_callback_count -= 1;
            }
        }
    }

    /// Clear all data (for teardown)
    fn clear(&self) {
        let mut data = self.data.lock().unwrap();
        data.clear();
    }
}

pub fn init_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<EventBus>()?;
    Ok(())
}
