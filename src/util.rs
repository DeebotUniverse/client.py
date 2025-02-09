use std::error::Error;
use std::io::{Cursor, Read};

use base64::{engine::general_purpose, Engine as _};
use liblzma::read::XzDecoder;
use liblzma::stream::Stream;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

pub fn decompress_base64_data(value: String) -> Result<Vec<u8>, Box<dyn Error>> {
    let bytes = general_purpose::STANDARD.decode(value)?;

    if is_zstd_compressed(&bytes) {
        decompress_zstd(&bytes)
    } else {
        decompress_lzma(bytes)
    }
}

fn decompress_lzma(mut bytes: Vec<u8>) -> Result<Vec<u8>, Box<dyn Error>> {
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

fn decompress_zstd(bytes: &[u8]) -> Result<Vec<u8>, Box<dyn Error>> {
    let mut decoder = zstd::Decoder::new(bytes)?;
    let mut result = Vec::new();
    decoder.read_to_end(&mut result)?;

    Ok(result)
}

fn is_zstd_compressed(bytes: &[u8]) -> bool {
    // Implement a check to determine if the data is zstd-compressed
    // That the data starts with the magic bytes of zstd-compressed data
    bytes.starts_with(&[0x28, 0xb5, 0x2f, 0xfd])
}

/// Decompress base64 decoded compressed string by using lzma or zstd
#[pyfunction(name = "decompress_base64_data")]
fn python_decompress_base64_data(value: String) -> Result<Vec<u8>, PyErr> {
    decompress_base64_data(value).map_err(|err| PyValueError::new_err(err.to_string()))
}

pub fn init_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(python_decompress_base64_data, m)?)?;
    Ok(())
}
