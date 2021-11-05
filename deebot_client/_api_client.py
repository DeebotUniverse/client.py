"""Internal api client module."""
import asyncio
import logging
from typing import Any, Dict, Optional
from urllib.parse import urljoin

from aiohttp import ClientResponseError

from .const import REALM
from .logging import get_logger
from .models import Configuration, Credentials

_LOGGER = get_logger(__name__)


def _get_portal_url(config: Configuration, path: str) -> str:
    subdomain = f"portal-{config.continent}" if config.country != "cn" else "portal"
    return urljoin(f"https://{subdomain}.ecouser.net/api/", path)


class _InternalApiClient:
    """Internal api client.

    Only required for AuthClient and ApiClient. For all other usecases use APIClient instead.
    """

    def __init__(self, config: Configuration):
        self._config = config

    async def post(
        self,
        path: str,
        json: Dict[str, Any],
        *,
        query_params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        credentials: Optional[Credentials] = None,
    ) -> Dict[str, Any]:
        """Perform a post request."""
        url = _get_portal_url(self._config, path)

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("calling api %s with %s", path, json)

        if credentials is not None:
            json.update(
                {
                    "auth": {
                        "with": "users",
                        "userid": credentials.user_id,
                        "realm": REALM,
                        "token": credentials.token,
                        "resource": self._config.device_id,
                    }
                }
            )

        try:
            async with self._config.session.post(
                url,
                json=json,
                params=query_params,
                headers=headers,
                timeout=60,
                ssl=self._config.verify_ssl,
            ) as res:
                res.raise_for_status()
                if res.status != 200:
                    _LOGGER.warning("Error calling API (%d): %s", res.status, path)
                    return {}

                response_data: Dict[str, Any] = await res.json()
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    _LOGGER.debug("got %s", response_data)
                return response_data
        except asyncio.TimeoutError:
            command = ""
            if "cmdName" in json:
                command = f"({json['cmdName']})"
            _LOGGER.warning("Timeout reached on api path: %s%s", path, command)
        except ClientResponseError as err:
            if err.status == 502:
                _LOGGER.info(
                    "Error calling API (502): Unfortunately the ecovacs api is unreliable. URL was: %s",
                    url,
                )
            else:
                _LOGGER.warning("Error calling API (%sd): %s", err.status, url)

        return {}
