use std::error::Error;

use base64::{engine::general_purpose, Engine as _};
use byteorder::{LittleEndian, ReadBytesExt};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::io::Cursor;

fn _decompress_7z_base64_data(value: String) -> Result<Vec<u8>, Box<dyn Error>> {
    let mut bytes = general_purpose::STANDARD.decode(value)?;

    // Insert required 0 bytes
    for _ in 0..=3 {
        bytes.insert(8, 0);
    }

    Ok(lzma::decompress(&bytes)?)
}

/// Decompress base64 decoded 7z compressed string.
#[pyfunction]
fn decompress_7z_base64_data(value: String) -> Result<Vec<u8>, PyErr> {
    Ok(_decompress_7z_base64_data(value).map_err(|err| PyValueError::new_err(err.to_string()))?)
}

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
            break; // Avoid out-of-bounds slice
        }

        // Read position_x and position_y
        let mut cursor = Cursor::new(&trace_points[i..i + 4]);
        let x = cursor.read_i16::<LittleEndian>()?;
        let y = cursor.read_i16::<LittleEndian>()?;

        // Extract point_data
        let point_data = trace_points[i + 4];

        // Determine connection status
        let connected = (point_data >> 7 & 1) == 0;

        // Append the TracePoint to trace_values
        trace_values.push(TracePoint { x, y, connected });
    }
    Ok(trace_values)
}

#[pyfunction]
/// Extract trace points from 7z compressed data string.
fn extract_trace_points(value: String) -> Result<Vec<TracePoint>, PyErr> {
    let decompressed_data = decompress_7z_base64_data(value)?;
    Ok(process_trace_points(&decompressed_data)
        .map_err(|err| PyValueError::new_err(err.to_string()))?)
}

/// Deebot client written in Rust
#[pymodule]
fn rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(decompress_7z_base64_data, m)?)?;
    m.add_function(wrap_pyfunction!(extract_trace_points, m)?)?;
    m.add_class::<TracePoint>()?;
    Ok(())
}
