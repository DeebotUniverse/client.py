use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use rsa::pkcs8::{DecodePublicKey, spki};
use rsa::rand_core::OsRng;
use rsa::{Pkcs1v15Encrypt, RsaPublicKey};

/// RSA public key
#[pyclass(name = "RsaPublicKey", frozen)]
struct PyRsaPublicKey {
    key: RsaPublicKey,
}

#[pymethods]
impl PyRsaPublicKey {
    /// Load an RSA public key from a DER encoded SubjectPublicKeyInfo structure.
    #[staticmethod]
    fn from_der(data: &[u8]) -> PyResult<Self> {
        RsaPublicKey::from_public_key_der(data)
            .map(|key| Self { key })
            .map_err(|err| match err {
                spki::Error::OidUnknown { .. } => PyValueError::new_err("not an RSA key"),
                err => PyValueError::new_err(err.to_string()),
            })
    }

    /// Encrypt data with PKCS#1 v1.5 padding.
    fn encrypt_pkcs1v15(&self, data: &[u8]) -> PyResult<Vec<u8>> {
        self.key
            .encrypt(&mut OsRng, Pkcs1v15Encrypt, data)
            .map_err(|err| PyValueError::new_err(err.to_string()))
    }
}

pub fn init_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyRsaPublicKey>()?;
    Ok(())
}
