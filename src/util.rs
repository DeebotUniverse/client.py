use std::error::Error;
use std::io::{Cursor, Read};

use base64::{engine::general_purpose, Engine as _};
use liblzma::read::XzDecoder;
use liblzma::stream::Stream;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

pub fn decompress_7z_base64_data(value: String) -> Result<Vec<u8>, Box<dyn Error>> {
    let mut bytes = general_purpose::STANDARD.decode(value)?;

    if bytes.len() < 8 {
        return Err("Invalid 7z compressed data".into());
    }

    for _ in 0..=3 {
        bytes.insert(8, 0);
    }

    let source = Cursor::new(&bytes);
    let stream = Stream::new_lzma_decoder(u64::MAX)?;
    let mut r = XzDecoder::new_stream(source, stream);
    let mut result = Vec::new();
    r.read_to_end(&mut result)?;

    Ok(result)
}

/// Decompress base64 decoded 7z compressed string.
#[pyfunction(name = "decompress_7z_base64_data")]
fn python_decompress_7z_base64_data(value: String) -> Result<Vec<u8>, PyErr> {
    Ok(decompress_7z_base64_data(value).map_err(|err| PyValueError::new_err(err.to_string()))?)
}

pub fn init_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(python_decompress_7z_base64_data, m)?)?;
    Ok(())
}
