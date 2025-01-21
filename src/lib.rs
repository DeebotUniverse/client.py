use std::error::Error;

use base64::{engine::general_purpose, Engine as _};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

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

/// Deebot client written in Rust
#[pymodule]
fn rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(decompress_7z_base64_data, m)?)?;
    Ok(())
}
