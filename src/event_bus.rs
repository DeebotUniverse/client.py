use std::sync::Arc;
use std::time::{Duration, Instant};
use dashmap::DashMap;
use pyo3::prelude::*;
use pyo3::types::*;
use tokio::sync::Mutex;

/// Event processing data for each event type
struct EventProcessingData {
    subscriber_callbacks: Arc<Mutex<Vec<PyObject>>>,
    last_event: Arc<Mutex<Option<PyObject>>>,
    last_event_time: Arc<Mutex<Instant>>,
    refresh_commands: Vec<PyObject>,
}

impl EventProcessingData {
    fn new(refresh_commands: Vec<PyObject>) -> Self {
        Self {
            subscriber_callbacks: Arc::new(Mutex::new(Vec::new())),
            last_event: Arc::new(Mutex::new(None)),
            last_event_time: Arc::new(Mutex::new(Instant::now() - Duration::from_secs(86400))), // Very old time
            refresh_commands,
        }
    }
}

/// High-performance Rust-based EventBus using Tokio
#[pyclass]
pub struct EventBus {
    event_processing_dict: Arc<DashMap<String, EventProcessingData>>,
    execute_command: PyObject,
    get_refresh_commands: PyObject,
}

#[pymethods]
impl EventBus {
    #[new]
    fn new(execute_command: PyObject, get_refresh_commands: PyObject) -> Self {
        Self {
            event_processing_dict: Arc::new(DashMap::new()),
            execute_command,
            get_refresh_commands,
        }
    }

    /// Check if there are subscribers for an event type
    fn has_subscribers(&self, event_type: Bound<'_, PyType>) -> PyResult<bool> {
        let event_type_name = event_type.name()?.to_string();
        
        if let Some(_data) = self.event_processing_dict.get(&event_type_name) {
            // Simple synchronous check for now
            Ok(false) // TODO: Implement properly
        } else {
            Ok(false)
        }
    }

    /// Subscribe to an event type with a callback  
    fn subscribe(&self, py: Python, event_type: Bound<'_, PyType>, _callback: PyObject) -> PyResult<PyObject> {
        let _event_type_name = event_type.name()?.to_string();
        let _event_processing_data = self.get_or_create_event_processing_data(py, &event_type)?;
        
        // Simple synchronous implementation for now
        // TODO: Make this properly async with Tokio
        
        // Create unsubscribe function
        let unsubscribe_fn = PyUnsubscribeFunction {};
        Py::new(py, unsubscribe_fn).map(|x| x.into_any())
    }

    /// Notify subscribers with an event, optionally with debouncing
    fn notify(&self, _py: Python, _event: PyObject, _debounce_time: Option<f64>) -> PyResult<()> {
        // Simple synchronous implementation for now
        // TODO: Implement debouncing and async notification
        Ok(())
    }

    /// Request manual refresh for an event type
    fn request_refresh(&self, _py: Python, _event_type: Bound<'_, PyType>) -> PyResult<()> {
        // Simple implementation
        Ok(())
    }

    /// Get the last event for an event type
    fn get_last_event(&self, _py: Python, event_type: Bound<'_, PyType>) -> PyResult<Option<PyObject>> {
        let event_type_name = event_type.name()?.to_string();
        
        if let Some(_data) = self.event_processing_dict.get(&event_type_name) {
            // TODO: Return actual last event
            Ok(None)
        } else {
            Ok(None)
        }
    }

    /// Add a callback that's called on first subscription
    fn add_on_subscription_callback(
        &self, 
        py: Python, 
        _event_type: Bound<'_, PyType>, 
        _callback: PyObject
    ) -> PyResult<PyObject> {
        // Simple implementation
        let unsubscribe_fn = PyUnsubscribeFunction {};
        Py::new(py, unsubscribe_fn).map(|x| x.into_any())
    }

    /// Teardown the event bus, cancelling all tasks and handles
    fn teardown<'a>(&self, py: Python<'a>) -> PyResult<Bound<'a, PyAny>> {
        // Simple teardown - return a coroutine-like object
        let none = py.None();
        Ok(none.into_bound(py))
    }
}

impl EventBus {
    /// Internal method to get or create event processing data
    fn get_or_create_event_processing_data(&self, py: Python, event_type: &Bound<'_, PyType>) -> PyResult<()> {
        let event_type_name = event_type.name()?.to_string();
        
        if self.event_processing_dict.get(&event_type_name).is_some() {
            Ok(())
        } else {
            // Get refresh commands for this event type
            let commands_result = self.get_refresh_commands.call1(py, (event_type,))?;
            let refresh_commands = commands_result.extract::<Vec<PyObject>>(py)?;
            
            let data = EventProcessingData::new(refresh_commands);
            self.event_processing_dict.insert(event_type_name, data);
            Ok(())
        }
    }
}

/// Helper class for unsubscribe functions
#[pyclass]
struct PyUnsubscribeFunction {
}

#[pymethods]
impl PyUnsubscribeFunction {
    fn __call__(&self, _py: Python) -> PyResult<()> {
        // TODO: Implement unsubscribe logic
        Ok(())
    }
}

/// Initialize the event_bus module
pub fn init_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<EventBus>()?;
    Ok(())
}