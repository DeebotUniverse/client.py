"""Deebot client module."""
from typing import Tuple

from ._api_client import _InternalApiClient
from .api_client import ApiClient
from .authentication import Authenticator
from .configuration import AuthenticationConfig


def create_instances(
    auth_config: AuthenticationConfig, account_id: str, password_hash: str
) -> tuple[Authenticator, ApiClient]:
    """Create an authenticator and api client instance."""
    internal_api_client = _InternalApiClient(auth_config)
    authenticator = Authenticator(
        auth_config, internal_api_client, account_id, password_hash
    )
    api_client = ApiClient(internal_api_client, authenticator)

    return authenticator, api_client
