"""Crypto helpers for tests."""

from __future__ import annotations

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

_NONCE_SIZE = 12


def decrypt(
    private_key: rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey, data: bytes
) -> bytes:
    """Decrypt data encrypted by deebot_client.rs.crypto.PublicKey.encrypt."""
    if isinstance(private_key, rsa.RSAPrivateKey):
        return private_key.decrypt(data, padding.PKCS1v15())

    point_size = 1 + 2 * ((private_key.curve.key_size + 7) // 8)
    ephemeral = data[:point_size]
    nonce = data[point_size : point_size + _NONCE_SIZE]
    ciphertext = data[point_size + _NONCE_SIZE :]

    shared_secret = private_key.exchange(
        ec.ECDH(),
        ec.EllipticCurvePublicKey.from_encoded_point(private_key.curve, ephemeral),
    )
    key = HKDF(hashes.SHA256(), 32, salt=None, info=ephemeral).derive(shared_secret)
    return AESGCM(key).decrypt(nonce, ciphertext, None)


def public_key_der(
    private_key: rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey,
) -> bytes:
    """Return the DER encoded SubjectPublicKeyInfo of the key."""
    return private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
