"""Authentication module."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from http import HTTPStatus
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin, urlparse

from aiohttp import ClientResponseError, ClientSession, ClientTimeout, hdrs

from .const import COUNTRY_CHINA, PATH_API_USERS_USER, REALM
from .exceptions import (
    ApiError,
    ApiTimeoutError,
    AuthenticationError,
    InvalidAuthenticationError,
)
from .logging_filter import get_logger
from .models import Credentials
from .util import cancel, create_task, md5
from .util.continents import get_continent_url_postfix
from .util.countries import get_ecovacs_country

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from .models import ApiDeviceInfo, StaticDeviceInfo
    from .ngiot_client import NgiotClient
    from .sst_authentication import SstAuthenticator


_LOGGER = get_logger(__name__)

_CLIENT_KEY = "1520391301804"
_CLIENT_SECRET = "6c319b2a5cd3e66e39159c2e28f2fce9"  # noqa: S105
_AUTH_CLIENT_KEY = "1520391491841"
_AUTH_CLIENT_SECRET = "77ef58ce3afbe337da74aa8c5ab963a9"  # noqa: S105
_USER_LOGIN_PATH_FORMAT = "/v1/private/{country}/{lang}/{deviceId}/{appCode}/{appVersion}/{channel}/{deviceType}/user/login"
_GLOBAL_AUTHCODE_PATH = "/v1/global/auth/getAuthCode"
_META = {
    "lang": "EN",
    "appCode": "global_e",
    "appVersion": "1.6.3",
    "channel": "google_play",
    "deviceType": "1",
}
MAX_RETRIES = 3
_NGIOT_BASE_URL_TEMPLATE = "https://api-base.dc-{region}.ww.ecouser.net"
_NGIOT_COMMAND_MODULE_PREFIX = "deebot_client.commands.ngiot"


@dataclass(frozen=True, kw_only=True)
class RestConfiguration:
    """Rest configuration."""

    session: ClientSession
    device_id: str
    country: str
    portal_url: str
    login_url: str
    auth_code_url: str


@dataclass(frozen=True, kw_only=True)
class NgiotConfiguration:
    """Optional overrides and defaults for NGIOT-backed devices."""

    base_url: str | None = None
    region: str | None = None
    user_agent: str = "okhttp/4.9.1"
    channel: str = "Android"
    protocol_version: str = "0.0.22"
    timezone_name: str = "UTC"
    timezone_offset_minutes: int = 0
    requested_ttl: int = 600
    refresh_skew: int = 60


def create_rest_config(
    session: ClientSession,
    *,
    device_id: str,
    alpha_2_country: str,
    override_rest_url: str | None = None,
) -> RestConfiguration:
    """Create configuration."""
    continent_postfix = get_continent_url_postfix(alpha_2_country)
    country = get_ecovacs_country(alpha_2_country)
    if override_rest_url:
        portal_url = login_url = auth_code_url = override_rest_url
    else:
        portal_url = f"https://portal{continent_postfix}.ecouser.net"
        country_url = country.lower()
        tld = "com" if alpha_2_country != COUNTRY_CHINA else country_url
        login_url = f"https://gl-{country_url}-api.ecovacs.{tld}"
        auth_code_url = f"https://gl-{country_url}-openapi.ecovacs.{tld}"

    return RestConfiguration(
        session=session,
        device_id=device_id,
        country=country,
        portal_url=portal_url,
        login_url=login_url,
        auth_code_url=auth_code_url,
    )


_TIMEOUT = ClientTimeout(60)


class _AuthClient:
    """Ecovacs auth client."""

    def __init__(
        self,
        config: RestConfiguration,
        account_id: str,
        password_hash: str,
    ) -> None:
        self._config = config
        self._account_id = account_id
        self._password_hash = password_hash

        self._meta: dict[str, str] = {
            **_META,
            "country": self._config.country.lower(),
            "deviceId": self._config.device_id,
        }

    async def login(self) -> Credentials:
        """Login using username and password."""
        _LOGGER.debug("Start login to EcovacsAPI")
        login_password_resp = await self.__call_login_api(
            self._account_id, self._password_hash
        )
        user_id = login_password_resp["uid"]

        auth_code = await self.__call_auth_api(
            login_password_resp["accessToken"], user_id
        )

        login_token_resp = await self.__call_login_by_it_token(user_id, auth_code)
        if login_token_resp["userId"] != user_id:
            _LOGGER.debug("Switching to shorter UID")
            user_id = login_token_resp["userId"]

        user_access_token = login_token_resp["token"]
        expires_at = int(
            time.time() + int(login_token_resp.get("last", 604800)) / 1000 * 0.99
        )

        _LOGGER.debug("Login to EcovacsAPI successfully")
        return Credentials(
            token=user_access_token,
            user_id=user_id,
            expires_at=expires_at,
        )

    async def __do_auth_response(
        self, url: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        async with self._config.session.get(
            url, params=params, timeout=_TIMEOUT
        ) as res:
            res.raise_for_status()

            content_type = res.headers.get(hdrs.CONTENT_TYPE, "").lower()
            json = await res.json(content_type=content_type)
            _LOGGER.debug("got %s", json)
            if json["code"] == "0000":
                data: dict[str, Any] = json["data"]
                return data
            if json["code"] in ["1005", "1010"]:
                raise InvalidAuthenticationError

            _LOGGER.error("call to %s failed with %s", url, json)
            msg = f"failure code {json['code']} ({json['msg']}) for call {url}"
            raise AuthenticationError(msg)

    async def __call_login_api(
        self, account_id: str, password_hash: str
    ) -> dict[str, Any]:
        _LOGGER.debug("calling login api")
        params: dict[str, str | int] = {
            "account": account_id,
            "password": password_hash,
            "requestId": md5(str(time.time())),
            "authTimespan": int(time.time() * 1000),
            "authTimeZone": "GMT-8",
        }

        url = urljoin(
            self._config.login_url, _USER_LOGIN_PATH_FORMAT.format(**self._meta)
        )

        if self._config.country == COUNTRY_CHINA:
            url += "CheckMobile"

        return await self.__do_auth_response(
            url, self.__sign(params, self._meta, _CLIENT_KEY, _CLIENT_SECRET)
        )

    @staticmethod
    def __sign(
        params: dict[str, str | int],
        additional_sign_params: Mapping[str, str | int],
        key: str,
        secret: str,
    ) -> dict[str, str | int]:
        sign_data: dict[str, str | int] = {**additional_sign_params, **params}
        sign_on_text = (
            key
            + "".join([k + "=" + str(sign_data[k]) for k in sorted(sign_data.keys())])
            + secret
        )
        params["authSign"] = md5(sign_on_text)
        params["authAppkey"] = key
        return params

    async def __call_auth_api(self, access_token: str, user_id: str) -> str:
        _LOGGER.debug("calling auth api")
        params: dict[str, str | int] = {
            "uid": user_id,
            "accessToken": access_token,
            "bizType": "ECOVACS_IOT",
            "deviceId": self._meta["deviceId"],
            "authTimespan": int(time.time() * 1000),
        }

        url = urljoin(self._config.auth_code_url, _GLOBAL_AUTHCODE_PATH)

        res = await self.__do_auth_response(
            url,
            self.__sign(
                params, {"openId": "global"}, _AUTH_CLIENT_KEY, _AUTH_CLIENT_SECRET
            ),
        )
        return str(res["authCode"])

    async def __call_login_by_it_token(
        self, user_id: str, auth_code: str
    ) -> dict[str, str]:
        data = {
            "edition": "ECOGLOBLE",
            "userId": user_id,
            "token": auth_code,
            "realm": REALM,
            "resource": self._config.device_id,
            "org": "ECOWW" if self._config.country != COUNTRY_CHINA else "ECOCN",
            "last": "",
            "country": self._config.country
            if self._config.country != COUNTRY_CHINA
            else "Chinese",
            "todo": "loginByItToken",
        }

        for i in range(3):
            resp = await self.post(PATH_API_USERS_USER, data)
            if resp["result"] == "ok":
                return resp
            if resp["result"] == "fail" and resp["error"] == "set token error.":
                _LOGGER.warning("loginByItToken set token error, attempt %d/3", i + 2)
                continue

            _LOGGER.error("call to %s failed with %s", PATH_API_USERS_USER, resp)
            msg = f"failure {resp['error']} ({resp['errno']}) for call {PATH_API_USERS_USER}"
            raise AuthenticationError(msg)

        raise AuthenticationError("failed to login with token")

    async def post(
        self,
        path: str,
        json: dict[str, Any],
        *,
        query_params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        credentials: Credentials | None = None,
    ) -> dict[str, Any]:
        """Perform a post request."""
        url = urljoin(self._config.portal_url, "api/" + path)
        logger_request_params = f"url={url}, params={query_params}, json={json}"

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

        for i in range(MAX_RETRIES):
            _LOGGER.debug(
                "Calling api(%d/%d): %s",
                i + 1,
                MAX_RETRIES,
                logger_request_params,
            )

            try:
                async with self._config.session.post(
                    url,
                    json=json,
                    params=query_params,
                    headers=headers,
                    timeout=_TIMEOUT,
                ) as res:
                    res.raise_for_status()

                    if res.status == HTTPStatus.OK:
                        response_data: dict[str, Any] = await res.json()
                        _LOGGER.debug(
                            "Success calling api %s, response=%s",
                            logger_request_params,
                            response_data,
                        )
                        return response_data

                    _LOGGER.debug(
                        "Error calling api %s, response=%s", logger_request_params, res
                    )
                    raise ApiError("Request failed") from ClientResponseError(
                        res.request_info,
                        res.history,
                        status=res.status,
                        message=str(res.reason),
                        headers=res.headers,
                    )
            except TimeoutError as ex:
                _LOGGER.debug("Timeout (%d) reached on path: %s", _TIMEOUT, path)
                raise ApiTimeoutError(path=path, timeout=_TIMEOUT) from ex
            except ClientResponseError as ex:
                _LOGGER.debug("Error: %s", logger_request_params, exc_info=True)
                if ex.status == HTTPStatus.BAD_GATEWAY:
                    seconds_to_sleep = 10
                    _LOGGER.info(
                        "Retry calling API due 502: Unfortunately the ecovacs api is unreliable. Retrying in %d seconds",
                        seconds_to_sleep,
                    )

                    await asyncio.sleep(seconds_to_sleep)
                    continue

                raise ApiError from ex

        raise ApiError("Unknown error occurred")


class Authenticator:
    """Authenticator."""

    def __init__(
        self,
        config: RestConfiguration,
        account_id: str,
        password_hash: str,
    ) -> None:
        self._config = config
        self._auth_client = _AuthClient(
            config,
            account_id,
            password_hash,
        )

        self._lock = asyncio.Lock()
        self._on_credentials_changed: set[
            Callable[[Credentials], Coroutine[Any, Any, None]]
        ] = set()
        self._credentials: Credentials | None = None
        self._refresh_handle: asyncio.TimerHandle | None = None
        self._tasks: set[asyncio.Future[Any]] = set()
        self._ngiot_config = NgiotConfiguration()
        self._ngiot_base_url: str | None = None
        self.sst_authenticator: SstAuthenticator | None = None
        self.ngiot_client: NgiotClient | None = None

    def configure_ngiot(
        self,
        *,
        base_url: str | None = None,
        region: str | None = None,
        user_agent: str = "okhttp/4.9.1",
        channel: str = "Android",
        protocol_version: str = "0.0.22",
        timezone_name: str = "UTC",
        timezone_offset_minutes: int = 0,
        requested_ttl: int = 600,
        refresh_skew: int = 60,
    ) -> None:
        """Store NGIOT defaults and optional region/base-url overrides.

        ``base_url`` wins over ``region``. If neither is configured, the
        runtime derives the SST endpoint from the device ``service.mqs`` host.
        """

        normalized_base_url = (
            self._normalize_base_url(base_url) if base_url is not None else None
        )
        normalized_region = (
            self._normalize_region(region) if region is not None else None
        )
        self._ngiot_config = NgiotConfiguration(
            base_url=normalized_base_url,
            region=normalized_region,
            user_agent=user_agent,
            channel=channel,
            protocol_version=protocol_version,
            timezone_name=timezone_name,
            timezone_offset_minutes=timezone_offset_minutes,
            requested_ttl=requested_ttl,
            refresh_skew=refresh_skew,
        )

    def attach_ngiot(
        self,
        *,
        base_url: str | None = None,
        region: str | None = None,
        user_agent: str = "okhttp/4.9.1",
        channel: str = "Android",
        protocol_version: str = "0.0.22",
        timezone_name: str = "UTC",
        timezone_offset_minutes: int = 0,
        requested_ttl: int = 600,
        refresh_skew: int = 60,
    ) -> None:
        """Attach NGIOT helpers immediately using an explicit base URL or region."""

        self.configure_ngiot(
            base_url=base_url,
            region=region,
            user_agent=user_agent,
            channel=channel,
            protocol_version=protocol_version,
            timezone_name=timezone_name,
            timezone_offset_minutes=timezone_offset_minutes,
            requested_ttl=requested_ttl,
            refresh_skew=refresh_skew,
        )
        resolved_base_url = self._resolve_configured_ngiot_base_url()
        if resolved_base_url is None:
            msg = (
                "attach_ngiot() requires base_url or region. "
                "For automatic per-device attachment, call configure_ngiot() and let "
                "ApiClient.get_devices() bootstrap NGIOT for matching hardware classes."
            )
            raise ApiError(msg)

        if self.ngiot_client is not None:
            if self._ngiot_base_url == resolved_base_url:
                return
            msg = (
                "NGIOT transport already attached with a different base URL. "
                "Use configure_ngiot() plus automatic device bootstrap, or call teardown() first."
            )
            raise ApiError(msg)

        self._create_ngiot_stack(resolved_base_url)

    async def ensure_ngiot_for_device(
        self,
        device_info: ApiDeviceInfo,
        static_device_info: StaticDeviceInfo,
    ) -> bool:
        """Attach NGIOT transport if the hardware profile uses NGIOT commands."""

        if not self._uses_ngiot(static_device_info):
            return False

        desired_base_url = self._resolve_ngiot_base_url(device_info)
        if self.ngiot_client is not None and self._ngiot_base_url == desired_base_url:
            return True

        if self.sst_authenticator is not None:
            if self._ngiot_base_url != desired_base_url:
                _LOGGER.info(
                    "Re-attaching NGIOT transport with region/base URL %s for %s",
                    desired_base_url,
                    device_info["class"],
                )
            await self.sst_authenticator.teardown()

        self.sst_authenticator = None
        self.ngiot_client = None
        self._ngiot_base_url = None
        self._create_ngiot_stack(desired_base_url)
        return True

    async def authenticate(self, *, force: bool = False) -> Credentials:
        """Authenticate on ecovacs servers."""
        async with self._lock:
            if (
                self._credentials is None
                or force
                or self._credentials.expires_at < time.time()
            ):
                _LOGGER.debug("Performing login")
                self._credentials = await self._auth_client.login()
                self._cancel_refresh_task()
                self._create_refresh_task(self._credentials)

                for on_changed in self._on_credentials_changed:
                    create_task(self._tasks, on_changed(self._credentials))

            return self._credentials

    def subscribe(
        self, callback: Callable[[Credentials], Coroutine[Any, Any, None]]
    ) -> Callable[[], None]:
        """Add callback on new credentials and return subscribe callback."""

        def unsubscribe() -> None:
            self._on_credentials_changed.remove(callback)

        self._on_credentials_changed.add(callback)
        return unsubscribe

    async def post_authenticated(
        self,
        path: str,
        json: dict[str, Any],
        *,
        query_params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform an authenticated post request."""
        return await self._auth_client.post(
            path,
            json,
            query_params=query_params,
            headers=headers,
            credentials=await self.authenticate(),
        )

    async def teardown(self) -> None:
        """Teardown authenticator."""
        self._cancel_refresh_task()
        if self.sst_authenticator is not None:
            await self.sst_authenticator.teardown()
            self.sst_authenticator = None
        self.ngiot_client = None
        self._ngiot_base_url = None
        await cancel(self._tasks)

    def _cancel_refresh_task(self) -> None:
        if self._refresh_handle and not self._refresh_handle.cancelled():
            self._refresh_handle.cancel()

    def _create_refresh_task(self, credentials: Credentials) -> None:
        def refresh() -> None:
            _LOGGER.debug("Refresh token")

            async def async_refresh() -> None:
                try:
                    await self.authenticate(force=True)
                except Exception:
                    _LOGGER.exception("An exception occurred during refreshing token")

            create_task(self._tasks, async_refresh())
            self._refresh_handle = None

        validity = (credentials.expires_at - time.time()) * 0.99
        self._refresh_handle = asyncio.get_event_loop().call_later(validity, refresh)

    def _create_ngiot_stack(self, base_url: str) -> None:
        from .ngiot_client import NgiotClient
        from .sst_authentication import SstAuthenticator

        normalized_base_url = self._normalize_base_url(base_url)
        self.sst_authenticator = SstAuthenticator(
            self._config.session,
            self,
            base_url=normalized_base_url,
            requested_ttl=self._ngiot_config.requested_ttl,
            refresh_skew=self._ngiot_config.refresh_skew,
        )
        self.ngiot_client = NgiotClient(
            self._config.session,
            self.sst_authenticator,
            user_agent=self._ngiot_config.user_agent,
            channel=self._ngiot_config.channel,
            protocol_version=self._ngiot_config.protocol_version,
            timezone_name=self._ngiot_config.timezone_name,
            timezone_offset_minutes=self._ngiot_config.timezone_offset_minutes,
        )
        self._ngiot_base_url = normalized_base_url

    def _resolve_configured_ngiot_base_url(self) -> str | None:
        if self._ngiot_config.base_url is not None:
            return self._ngiot_config.base_url
        if self._ngiot_config.region is not None:
            return self._format_ngiot_base_url(self._ngiot_config.region)
        return None

    def _resolve_ngiot_base_url(self, device_info: ApiDeviceInfo) -> str:
        configured_base_url = self._resolve_configured_ngiot_base_url()
        if configured_base_url is not None:
            return configured_base_url

        service = device_info.get("service")
        if isinstance(service, Mapping):
            mqs_host = service.get("mqs")
            if isinstance(mqs_host, str) and mqs_host:
                return self._derive_ngiot_base_url_from_mqs(mqs_host)

        msg = (
            f'Could not resolve NGIOT base URL for device class "{device_info["class"]}". '
            "Configure an explicit region or base_url before device bootstrap."
        )
        raise ApiError(msg)

    @classmethod
    def _uses_ngiot(cls, static_device_info: StaticDeviceInfo) -> bool:
        return cls._object_uses_ngiot(getattr(static_device_info, "capabilities", None))

    @classmethod
    def _object_uses_ngiot(cls, value: object) -> bool:
        if value is None:
            return False
        if isinstance(value, type):
            return cls._is_ngiot_module(value.__module__)
        if cls._is_ngiot_module(value.__class__.__module__):
            return True
        if isinstance(value, Mapping):
            return any(
                cls._object_uses_ngiot(key) or cls._object_uses_ngiot(item)
                for key, item in value.items()
            )
        if isinstance(value, (list, tuple, set, frozenset)):
            return any(cls._object_uses_ngiot(item) for item in value)
        if is_dataclass(value):
            return any(
                cls._object_uses_ngiot(getattr(value, field.name))
                for field in fields(value)
            )
        return False

    @staticmethod
    def _is_ngiot_module(module_name: str) -> bool:
        return module_name.startswith(_NGIOT_COMMAND_MODULE_PREFIX)

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        parsed = urlparse(base_url)
        if parsed.scheme and parsed.netloc:
            host = parsed.netloc
        else:
            host = base_url
        return f"https://{host.strip().rstrip('/')}"

    @staticmethod
    def _normalize_region(region: str) -> str:
        normalized = region.strip().lower()
        if normalized.startswith("dc-"):
            normalized = normalized[3:]
        return normalized

    @classmethod
    def _format_ngiot_base_url(cls, region: str) -> str:
        return _NGIOT_BASE_URL_TEMPLATE.format(region=cls._normalize_region(region))

    @classmethod
    def _derive_ngiot_base_url_from_mqs(cls, mqs_host: str) -> str:
        parsed = urlparse(mqs_host)
        host = parsed.netloc or parsed.path
        host = host.strip().rstrip("/")
        if not host:
            msg = f'Could not derive NGIOT base URL from mqs host "{mqs_host}"'
            raise ApiError(msg)
        if host.startswith("api-base."):
            return cls._normalize_base_url(host)
        if host.startswith("api-ngiot."):
            return cls._normalize_base_url("api-base." + host.split(".", 1)[1])
        if "." in host:
            return cls._normalize_base_url("api-base." + host.split(".", 1)[1])
        msg = f'Could not derive NGIOT base URL from mqs host "{mqs_host}"'
        raise ApiError(msg)
