"""Internal api client module."""
import asyncio
from typing import Any, Optional
from urllib.parse import urljoin

from aiohttp import ClientResponseError

from .const import REALM
from .logging_filter import get_logger
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
        json: dict[str, Any],
        *,
        query_params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
        credentials: Optional[Credentials] = None,
    ) -> dict[str, Any]:
        """Perform a post request."""
        url = _get_portal_url(self._config, path)

        logger_msg = f"calling api: url={url}, params={query_params}, json={json}"
        _LOGGER.debug(logger_msg)

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
                if res.status == 200:
                    response_data: dict[str, Any] = await res.json()
                    _LOGGER.debug("Success: %s, response=%s", logger_msg, response_data)
                    return response_data

                _LOGGER.warning("Error calling API (%d): %s", res.status, path)
                _LOGGER.debug("Error: %s, status=%s", logger_msg, res.status)
        except asyncio.TimeoutError:
            command = ""
            if "cmdName" in json:
                command = f"({json['cmdName']})"
            _LOGGER.warning("Timeout reached on api path: %s%s", path, command)
            _LOGGER.debug("Timeout on %s", logger_msg)
        except ClientResponseError as err:
            if err.status == 502:
                _LOGGER.info(
                    "Error calling API (502): Unfortunately the ecovacs api is unreliable. URL was: %s",
                    url,
                )
            else:
                _LOGGER.warning("Error calling API (%d): %s", err.status, url)
            _LOGGER.debug("Error: %s, status=%s", logger_msg, err.status)

        return {}
