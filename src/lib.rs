use base64::{engine::general_purpose, Engine as _};
use pyo3::prelude::*;

#[pyfunction]
fn decompress_7z_base64_data(input: String) -> PyResult<String> {
    // todo add error handling
    let mut bytes = general_purpose::STANDARD.decode(input).unwrap();
    bytes.insert(8, 0);
    bytes.insert(8, 0);
    bytes.insert(8, 0);
    bytes.insert(8, 0);
    let decompressed = lzma::decompress(&bytes).unwrap();
    Ok(String::from_utf8(decompressed).unwrap())
}

#[pymodule]
fn rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(decompress_7z_base64_data, m)?)?;
    Ok(())
}
