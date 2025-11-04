use log::error;
use std::error::Error;
use std::io::{Cursor, Read};

use base64::{Engine as _, engine::general_purpose};
use liblzma::read::XzDecoder;
use liblzma::stream::Stream;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

const ZSTD_MAGIC: [u8; 4] = [0x28, 0xb5, 0x2f, 0xfd];

/// Fast check if compressed data is zstd.
#[inline]
fn is_zstd_compressed(bytes: &[u8]) -> bool {
    bytes.len() >= 4 && bytes[..4] == ZSTD_MAGIC
}

pub fn decompress_base64_data(value: &str) -> Result<Vec<u8>, Box<dyn Error>> {
    let bytes = general_purpose::STANDARD.decode(value)?;
    if is_zstd_compressed(&bytes) {
        decompress_zstd(&bytes)
    } else {
        decompress_lzma(&bytes)
    }
}

/// Decompress LZMA data, avoiding Vec insert overhead.
fn decompress_lzma(bytes: &[u8]) -> Result<Vec<u8>, Box<dyn Error>> {
    if bytes.len() < 8 {
        return Err("Invalid 7z compressed data".into());
    }

    // Form tailored header without repeated inserts (much faster)
    let mut full = Vec::with_capacity(bytes.len() + 4);
    full.extend_from_slice(&bytes[..8]);
    full.extend_from_slice(&[0, 0, 0, 0]);
    full.extend_from_slice(&bytes[8..]);

    let source = Cursor::new(full);
    let stream = Stream::new_lzma_decoder(u64::MAX)?;
    let mut r = XzDecoder::new_stream(source, stream);
    let mut result = Vec::new();
    r.read_to_end(&mut result)?;
    Ok(result)
}

fn decompress_zstd(bytes: &[u8]) -> Result<Vec<u8>, Box<dyn Error>> {
    let mut decoder = zstd::Decoder::new(bytes)?;
    let mut result = Vec::new();
    decoder.read_to_end(&mut result)?;
    Ok(result)
}

/// Decompress base64 decoded compressed string by using lzma or zstd
#[pyfunction(name = "decompress_base64_data")]
fn python_decompress_base64_data(value: &str) -> Result<Vec<u8>, PyErr> {
    decompress_base64_data(value).map_err(|err| {
        error!("Error decompressing base64 data: {err}; value:{value}");
        PyValueError::new_err(err.to_string())
    })
}

/// Parse comma-separated integers from a string.
/// Empty strings are filtered out automatically.
///
/// Example: "1,2,3,," -> [1, 2, 3]
#[pyfunction(name = "parse_csv_ints")]
fn python_parse_csv_ints(value: &str) -> Result<Vec<i32>, PyErr> {
    parse_csv_ints(value).map_err(|err| {
        error!("Error parsing comma-separated integers: {err}; value:{value}");
        PyValueError::new_err(err.to_string())
    })
}

/// Parse comma-separated integers from a string, converting via float first.
/// This matches Python's behavior: int(float(x))
/// Empty strings are filtered out automatically.
///
/// Example: "1.5,2.7,3.0,," -> [1, 2, 3]
#[pyfunction(name = "parse_csv_ints_via_float")]
fn python_parse_csv_ints_via_float(value: &str) -> Result<Vec<i32>, PyErr> {
    parse_csv_ints_via_float(value).map_err(|err| {
        error!("Error parsing comma-separated floats to ints: {err}; value:{value}");
        PyValueError::new_err(err.to_string())
    })
}

pub fn parse_csv_ints(value: &str) -> Result<Vec<i32>, Box<dyn Error>> {
    value
        .split(',')
        .filter(|s| !s.is_empty())
        .map(|s| s.trim().parse::<i32>().map_err(|e| e.into()))
        .collect()
}

pub fn parse_csv_ints_via_float(value: &str) -> Result<Vec<i32>, Box<dyn Error>> {
    value
        .split(',')
        .filter(|s| !s.is_empty())
        .map(|s| {
            s.trim()
                .parse::<f64>()
                .map(|f| f as i32)
                .map_err(|e| e.into())
        })
        .collect()
}

pub fn init_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(python_decompress_base64_data, m)?)?;
    m.add_function(wrap_pyfunction!(python_parse_csv_ints, m)?)?;
    m.add_function(wrap_pyfunction!(python_parse_csv_ints_via_float, m)?)?;
    Ok(())
}
