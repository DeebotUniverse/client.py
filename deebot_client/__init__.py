"""Deebot client module."""
from typing import Tuple

from ._api_client import _InternalApiClient
from .api_client import ApiClient
from .authentication import Authenticator
from .models import Configuration


def create_instances(
    config: Configuration, account_id: str, password_hash: str
) -> tuple[Authenticator, ApiClient]:
    """Create a authenticator and api client instance."""
    internal_api_client = _InternalApiClient(config)
    authenticator = Authenticator(
        config, internal_api_client, account_id, password_hash
    )
    api_client = ApiClient(internal_api_client, authenticator)

    return authenticator, api_client
