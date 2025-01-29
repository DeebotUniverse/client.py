use std::error::Error;

use super::util::decompress_7z_base64_data;
use byteorder::{LittleEndian, ReadBytesExt};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::io::Cursor;

/// Trace point
#[pyclass]
struct TracePoint {
    #[pyo3(get)]
    x: i16,

    #[pyo3(get)]
    y: i16,

    #[pyo3(get)]
    connected: bool,
}

#[pymethods]
impl TracePoint {
    #[new]
    fn new(x: i16, y: i16, connected: bool) -> Self {
        TracePoint { x, y, connected }
    }
}

fn process_trace_points(trace_points: &[u8]) -> Result<Vec<TracePoint>, Box<dyn Error>> {
    let mut trace_values = Vec::new();
    for i in (0..trace_points.len()).step_by(5) {
        if i + 4 >= trace_points.len() {
            return Err("Invalid trace points length".into());
        }

        let mut cursor = Cursor::new(&trace_points[i..i + 4]);
        let x = cursor.read_i16::<LittleEndian>()?;
        let y = cursor.read_i16::<LittleEndian>()?;

        // Determine connection status
        let connected = (trace_points[i + 4] >> 7 & 1) == 0;

        trace_values.push(TracePoint { x, y, connected });
    }
    Ok(trace_values)
}

fn extract_trace_points(value: String) -> Result<Vec<TracePoint>, Box<dyn Error>> {
    let decompressed_data = decompress_7z_base64_data(value)?;
    process_trace_points(&decompressed_data)
}

#[pyfunction(name = "extract_trace_points")]
/// Extract trace points from 7z compressed data string.
fn python_extract_trace_points(value: String) -> Result<Vec<TracePoint>, PyErr> {
    extract_trace_points(value).map_err(|err| PyValueError::new_err(err.to_string()))
}

pub fn init_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(python_extract_trace_points, m)?)?;
    m.add_class::<TracePoint>()?;
    Ok(())
}
