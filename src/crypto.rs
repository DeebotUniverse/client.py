use aes_gcm::aead::{Aead, Nonce};
use aes_gcm::{Aes256Gcm, Key as AesKey, KeyInit};
use p256::NistP256;
use p256::ecdh::EphemeralSecret;
use p256::elliptic_curve::Generate;
use p256::elliptic_curve::sec1::ToSec1Point;
use p256::elliptic_curve::zeroize::Zeroizing;
use p256::pkcs8::AssociatedOid;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use rsa::pkcs8::spki::SubjectPublicKeyInfoRef;
use rsa::pkcs8::spki::der::Decode;
use rsa::rand_core::OsRng;
use rsa::traits::PublicKeyParts;
use rsa::{Pkcs1v15Encrypt, RsaPublicKey};
use sha2::Sha256;

enum Key {
    Rsa(RsaPublicKey),
    P256(p256::PublicKey),
}

impl Key {
    /// Load a key from a DER encoded SubjectPublicKeyInfo structure.
    fn from_der(data: &[u8]) -> Result<Self, String> {
        let spki = SubjectPublicKeyInfoRef::from_der(data).map_err(|e| e.to_string())?;
        let oid = spki.algorithm.oid;
        if oid == rsa::pkcs1::ALGORITHM_OID {
            return RsaPublicKey::try_from(spki)
                .map(Self::Rsa)
                .map_err(|e| e.to_string());
        }
        // rsa and p256 depend on different const-oid versions, so compare the DER encoding
        if oid.as_bytes() != p256::elliptic_curve::ALGORITHM_OID.as_bytes() {
            return Err(format!("unsupported key algorithm {oid}"));
        }

        let curve = spki.algorithm.parameters_oid().map_err(|e| e.to_string())?;
        if curve.as_bytes() != NistP256::OID.as_bytes() {
            return Err(format!("unsupported elliptic curve {curve}"));
        }
        let public_key = spki
            .subject_public_key
            .as_bytes()
            .ok_or_else(|| "invalid public key bit string".to_owned())?;
        p256::PublicKey::from_sec1_bytes(public_key)
            .map(Self::P256)
            .map_err(|e| e.to_string())
    }
}

/// Encrypt data with ECIES.
///
/// The output is `ephemeral public key (SEC1 uncompressed) || nonce (12 bytes) ||
/// ciphertext || tag (16 bytes)`. The AES-256-GCM key is derived with
/// HKDF-SHA256 from the ECDH shared secret, without salt and the ephemeral public
/// key as info.
fn ecies_encrypt(public_key: &p256::PublicKey, data: &[u8]) -> Result<Vec<u8>, String> {
    let ephemeral = EphemeralSecret::try_generate().map_err(|e| e.to_string())?;
    let ephemeral_public = ephemeral.public_key().to_sec1_point(false);

    let mut key = Zeroizing::new([0u8; 32]);
    ephemeral
        .diffie_hellman(public_key)
        .extract::<Sha256>(None)
        .expand(ephemeral_public.as_bytes(), key.as_mut())
        .map_err(|e| e.to_string())?;

    let cipher_key: &AesKey<Aes256Gcm> = (&*key).into();
    let cipher = Aes256Gcm::new(cipher_key);
    let nonce = Nonce::<Aes256Gcm>::try_generate().map_err(|e| e.to_string())?;
    let ciphertext = cipher
        .encrypt(&nonce, data)
        .map_err(|_| "encryption failed".to_owned())?;

    let mut result = Vec::with_capacity(ephemeral_public.len() + nonce.len() + ciphertext.len());
    result.extend_from_slice(ephemeral_public.as_bytes());
    result.extend_from_slice(&nonce);
    result.extend_from_slice(&ciphertext);
    Ok(result)
}

/// RSA or elliptic curve P-256 public key
#[pyclass(name = "PublicKey", frozen)]
struct PyPublicKey {
    key: Key,
}

#[pymethods]
impl PyPublicKey {
    /// Load a public key from a DER encoded SubjectPublicKeyInfo structure.
    #[staticmethod]
    fn from_der(data: &[u8]) -> PyResult<Self> {
        Key::from_der(data)
            .map(|key| Self { key })
            .map_err(PyValueError::new_err)
    }

    /// Key algorithm, e.g. "RSA-2048" or "EC-P256".
    #[getter]
    fn algorithm(&self) -> String {
        match &self.key {
            Key::Rsa(key) => format!("RSA-{}", key.size() * 8),
            Key::P256(_) => "EC-P256".to_owned(),
        }
    }

    /// Encrypt data with PKCS#1 v1.5 padding (RSA) or ECIES (EC).
    fn encrypt(&self, data: &[u8]) -> PyResult<Vec<u8>> {
        match &self.key {
            Key::Rsa(key) => key
                .encrypt(&mut OsRng, Pkcs1v15Encrypt, data)
                .map_err(|e| e.to_string()),
            Key::P256(key) => ecies_encrypt(key, data),
        }
        .map_err(PyValueError::new_err)
    }
}

pub fn init_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyPublicKey>()?;
    Ok(())
}
