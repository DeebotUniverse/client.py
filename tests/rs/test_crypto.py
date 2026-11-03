"""Test rust crypto functions."""

from __future__ import annotations

import base64
import re

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
import pytest

from deebot_client.rs.crypto import PublicKey
from tests.helpers.crypto import decrypt, public_key_der

# Public key of a self hosted server, which uses the TLS certificate key
_SELF_HOSTED_EC_KEY = "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE6fEfOigFHViaSmG33CtWLNZtphdTvc9c1QB/uL8lkIk7J7dcT6/ORtEj7NZwg4mzl3SYi/n9DARMg/kBaj2n1Q=="

_KEYS: dict[str, rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey] = {
    "RSA-2048": rsa.generate_private_key(public_exponent=65537, key_size=2048),
    "EC-P256": ec.generate_private_key(ec.SECP256R1()),
}


@pytest.mark.parametrize("algorithm", _KEYS)
def test_encrypt(algorithm: str) -> None:
    private_key = _KEYS[algorithm]
    key = PublicKey.from_der(public_key_der(private_key))
    data = b"user@example.com"

    encrypted = key.encrypt(data)

    assert key.algorithm == algorithm
    assert isinstance(encrypted, bytes)
    assert decrypt(private_key, encrypted) == data
    # RSA PKCS1v15 padding and ECIES are random
    assert key.encrypt(data) != encrypted


def test_self_hosted_ec_key() -> None:
    key = PublicKey.from_der(base64.b64decode(_SELF_HOSTED_EC_KEY))

    assert key.algorithm == "EC-P256"
    # uncompressed point (65) + nonce (12) + data (4) + tag (16)
    assert len(key.encrypt(b"data")) == 97


def test_encrypt_rsa_data_too_long() -> None:
    key = PublicKey.from_der(public_key_der(_KEYS["RSA-2048"]))

    # 2048 bit key with PKCS1v15 padding allows max 245 bytes
    with pytest.raises(ValueError, match="message too long"):
        key.encrypt(b"a" * 246)


def test_encrypt_ec_long_data() -> None:
    private_key = _KEYS["EC-P256"]
    key = PublicKey.from_der(public_key_der(private_key))
    data = b"a" * 1024

    assert decrypt(private_key, key.encrypt(data)) == data


@pytest.mark.parametrize("data", [b"", b"not-a-key"])
def test_from_der_invalid(data: bytes) -> None:
    with pytest.raises(ValueError, match=r".+"):
        PublicKey.from_der(data)


@pytest.mark.parametrize(
    ("curve", "oid"),
    [
        (ec.SECP256K1(), "1.3.132.0.10"),
        (ec.SECP384R1(), "1.3.132.0.34"),
        (ec.SECP521R1(), "1.3.132.0.35"),
    ],
)
def test_from_der_unsupported_curve(curve: ec.EllipticCurve, oid: str) -> None:
    der = public_key_der(ec.generate_private_key(curve))

    with pytest.raises(
        ValueError, match=rf"^unsupported elliptic curve {re.escape(oid)}$"
    ):
        PublicKey.from_der(der)


def test_from_der_unsupported_algorithm() -> None:
    der = (
        ed25519.Ed25519PrivateKey.generate()
        .public_key()
        .public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    with pytest.raises(ValueError, match=r"^unsupported key algorithm 1\.3\.101\.112$"):
        PublicKey.from_der(der)
