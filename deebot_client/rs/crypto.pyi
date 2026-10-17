class RsaPublicKey:
    """RSA public key."""

    @staticmethod
    def from_der(data: bytes) -> RsaPublicKey:
        """Load an RSA public key from a DER encoded SubjectPublicKeyInfo structure.

        Raises ValueError if the data is invalid or not an RSA key.
        """

    def encrypt_pkcs1v15(self, data: bytes) -> bytes:
        """Encrypt data with PKCS#1 v1.5 padding.

        Raises ValueError if the data is too long for the key.
        """
