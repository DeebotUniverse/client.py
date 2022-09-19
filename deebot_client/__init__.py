"""Deebot client module."""

from .api_client import ApiClient
from .authentication import Authenticator
from .models import Configuration


def create_instances(
    config: Configuration, account_id: str, password_hash: str
) -> tuple[Authenticator, ApiClient]:
    """Create a authenticator and api client instance."""
    authenticator = Authenticator(config, account_id, password_hash)
    client = ApiClient(authenticator)

    return authenticator, client
