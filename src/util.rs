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
    let full = restore_lzma_alone_header(bytes)?;

    let source = Cursor::new(full);
    let stream = Stream::new_lzma_decoder(u64::MAX)?;
    let mut r = XzDecoder::new_stream(source, stream);
    let mut result = Vec::new();
    r.read_to_end(&mut result)?;
    Ok(result)
}

/// Restore the four missing high bytes of the LZMA-Alone size field.
fn restore_lzma_alone_header(bytes: &[u8]) -> Result<Vec<u8>, Box<dyn Error>> {
    if bytes.len() < 9 {
        return Err("Invalid 7z compressed data".into());
    }

    // The trimmed representation retains properties (5 bytes) and all four
    // low size bytes. Restore the missing high size bytes after byte 8.
    let mut full = Vec::with_capacity(bytes.len() + 4);
    full.extend_from_slice(&bytes[..9]);
    full.extend_from_slice(&[0, 0, 0, 0]);
    full.extend_from_slice(&bytes[9..]);
    Ok(full)
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
        error!("Error decompressing base64 data: {err}");
        PyValueError::new_err(err.to_string())
    })
}

pub fn init_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(python_decompress_base64_data, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::restore_lzma_alone_header;

    #[test]
    fn restores_high_size_bytes_after_all_four_low_size_bytes() {
        let trimmed = [
            0x5d, 0x00, 0x00, 0x04, 0x00, 0x11, 0x22, 0x33, 0x44, 0xaa, 0xbb,
        ];

        let restored = restore_lzma_alone_header(&trimmed).unwrap();

        assert_eq!(&restored[..9], &trimmed[..9]);
        assert_eq!(&restored[9..13], &[0, 0, 0, 0]);
        assert_eq!(&restored[13..], &trimmed[9..]);
    }
}
