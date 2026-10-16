"""Test rust crypto functions."""

from __future__ import annotations

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
import pytest

from deebot_client.rs.crypto import RsaPublicKey


def _der(public_key: rsa.RSAPublicKey | ec.EllipticCurvePublicKey) -> bytes:
    return public_key.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )


@pytest.fixture(scope="module")
def private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def test_encrypt_pkcs1v15(private_key: rsa.RSAPrivateKey) -> None:
    key = RsaPublicKey.from_der(_der(private_key.public_key()))
    data = b"user@example.com"

    encrypted = key.encrypt_pkcs1v15(data)

    assert isinstance(encrypted, bytes)
    assert len(encrypted) == 256
    assert private_key.decrypt(encrypted, padding.PKCS1v15()) == data
    # PKCS1v15 padding is random
    assert key.encrypt_pkcs1v15(data) != encrypted


def test_encrypt_pkcs1v15_data_too_long(private_key: rsa.RSAPrivateKey) -> None:
    key = RsaPublicKey.from_der(_der(private_key.public_key()))

    # 2048 bit key with PKCS1v15 padding allows max 245 bytes
    with pytest.raises(ValueError, match="message too long"):
        key.encrypt_pkcs1v15(b"a" * 246)


@pytest.mark.parametrize("data", [b"", b"not-a-key"])
def test_from_der_invalid(data: bytes) -> None:
    with pytest.raises(ValueError, match=r".+"):
        RsaPublicKey.from_der(data)


def test_from_der_not_rsa() -> None:
    der = _der(ec.generate_private_key(ec.SECP256R1()).public_key())

    with pytest.raises(ValueError, match=r"^not an RSA key$"):
        RsaPublicKey.from_der(der)
