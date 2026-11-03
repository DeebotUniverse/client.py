class PublicKey:
    """RSA or elliptic curve P-256 public key."""

    @staticmethod
    def from_der(data: bytes) -> PublicKey:
        """Load a public key from a DER encoded SubjectPublicKeyInfo structure.

        Raises ValueError if the data is invalid or the key type is unsupported.
        """

    @property
    def algorithm(self) -> str:
        """Key algorithm, e.g. "RSA-2048" or "EC-P256"."""

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data.

        RSA keys use PKCS#1 v1.5 padding.
        EC keys use ECIES: ephemeral ECDH on P-256, HKDF-SHA256 (no salt,
        info = ephemeral public key) and AES-256-GCM. The result is
        ephemeral public key (SEC1 uncompressed) || nonce (12 bytes) || ciphertext || tag (16 bytes).

        Raises ValueError if the data is too long for an RSA key.
        """
