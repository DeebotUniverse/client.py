use pyo3::prelude::*;

mod map;
mod util;

/// Deebot client written in Rust
#[pymodule]
fn rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    pyo3_log::init();

    register_child_module(m, "map", map::init_module)?;
    register_child_module(m, "util", util::init_module)?;
    Ok(())
}

fn register_child_module(
    parent_module: &Bound<'_, PyModule>,
    name: &str,
    func: fn(&Bound<'_, PyModule>) -> PyResult<()>,
) -> PyResult<()> {
    let child_module = PyModule::new(parent_module.py(), name)?;
    func(&child_module)?;

    // https://github.com/PyO3/pyo3/issues/1517#issuecomment-808664021
    // https://github.com/PyO3/pyo3/issues/759
    let _ = Python::with_gil(|py| {
        py.import("sys")?
            .getattr("modules")?
            .set_item(&format!("deebot_client.rs.{}", name), &child_module)
    });

    parent_module.add_submodule(&child_module)
}
