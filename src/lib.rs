use pyo3::prelude::*;

mod map;
mod util;

/// Deebot client written in Rust
#[pymodule]
fn rs(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    register_submodule(py, m, map::init_module)?;
    register_submodule(py, m, util::init_module)?;
    Ok(())
}

fn register_submodule<F>(
    py: Python<'_>,
    parent_module: &Bound<'_, PyModule>,
    submodule: F,
) -> PyResult<()>
where
    F: Fn(&Bound<'_, PyModule>) -> PyResult<()>,
{
    let parts: Vec<&str> = std::any::type_name::<F>().split("::").collect();
    let module_name = parts[parts.len() - 2];

    let child_module = PyModule::new(parent_module.py(), module_name)?;
    submodule(&child_module)?;

    // https://github.com/PyO3/pyo3/issues/1517#issuecomment-808664021
    // https://github.com/PyO3/pyo3/issues/759
    PyModule::import(py, "sys")?
        .getattr("modules")?
        .set_item(&format!("deebot_client.rs.{}", module_name), &child_module)?;

    parent_module.add_submodule(&child_module)
}
