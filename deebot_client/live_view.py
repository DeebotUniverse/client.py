"""Live view (camera) via the ECOVACS cloud and AWS Kinesis Video Streams WebRTC.

Flow:
1. ECOVACS ``start_watch`` returns temporary AWS credentials for a Kinesis
   signaling channel and starts the camera of the robot.
2. The Kinesis signaling endpoint and ICE servers are requested.
3. The result is a go2rtc source (``webrtc:wss://...#format=kinesis``), so the
   WebRTC connection itself is done by go2rtc (e.g. the one of Home Assistant).

The ECOVACS part is based on https://github.com/imcdo17-cyber/home-assistant-ecovacs-live
(MIT License, Copyright (c) 2026 ECOVACS Live View contributors).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import hashlib
import hmac
import secrets
import string
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, quote, urlparse, urlunparse

from aiohttp import ClientTimeout
import orjson

from .exceptions import DeebotError
from .logging_filter import get_logger

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from .authentication import Authenticator
    from .models import ApiDeviceInfo

_LOGGER = get_logger(__name__)

_APP_ID = "ecovacs"
_APP_VERSION = "3.14.0"
_APP_CHANNEL = "google_play"
_VIDEO_API_VERSION = "2.1.0"
_SIGNING_PREFIX = "ecovacs2ea31cf06e6711eaa0aff7b9558a534e"
_REALM = "ecouser.net"
_PATH_START_WATCH = "/api/appsvr/akvs/start_watch/v2"
_SERVICE = "kinesisvideo"
_CODE_WRONG_PIN = 30010
# The signed signaling url is valid for 5 minutes
SIGNED_URL_VALIDITY = 299
_TIMEOUT = ClientTimeout(30)


class PinEncoding(StrEnum):
    """Encoding of the live view PIN."""

    ECO_MD5 = "eco_md5"  # DEEBOT vacuums
    GOAT_MD5 = "goat_md5"  # GOAT O800 RTK
    GOAT_SHA256 = "goat_sha256"  # GOAT O1000


def encode_pin(pin: str, encoding: PinEncoding) -> str:
    """Encode the live view PIN."""
    match encoding:
        case PinEncoding.GOAT_MD5:
            return hashlib.md5(f"goat_{pin}".encode()).hexdigest()  # noqa: S324
        case PinEncoding.GOAT_SHA256:
            return hashlib.sha256(f"goat_{pin}".encode()).hexdigest()
        case _:
            return hashlib.md5(f"eco_{pin}".encode()).hexdigest()  # noqa: S324


class LiveViewError(DeebotError):
    """Live view could not be started."""


class LiveViewPinError(LiveViewError):
    """The live view PIN is wrong."""


@dataclass(frozen=True)
class _KinesisSession:
    region: str
    channel: str
    client_id: str
    access_key_id: str
    secret_access_key: str
    session_token: str


@dataclass(frozen=True)
class LiveViewSource:
    """go2rtc source for the live view."""

    url: str
    created: float


def _random_id(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _start_watch(
    authenticator: Authenticator,
    device_info: ApiDeviceInfo,
    pin_hash: str,
) -> _KinesisSession:
    config = authenticator.config
    credentials = await authenticator.authenticate()
    timestamp_ms = str(int(time.time() * 1000))
    auth = {
        "with": "users",
        "userid": credentials.user_id,
        "realm": _REALM,
        "token": credentials.token,
        "resource": config.device_id,
    }
    params = {
        "videoTrackId": _random_id(10),
        "lang": "en",
        "plat": "Android",
        "av": _VIDEO_API_VERSION,
        "did": device_info["did"],
        "mid": device_info["class"],
        "res": device_info["resource"],
        "pwd": pin_hash,
        "auth": orjson.dumps(auth).decode(),
        "channel": _APP_CHANNEL,
    }
    headers = {
        "country": config.country,
        "Accept": "application/json",
        "sign": hashlib.sha1(  # noqa: S324
            f"{_SIGNING_PREFIX}{timestamp_ms}".encode()
        ).hexdigest(),
        "userid": credentials.user_id,
        "token": credentials.token,
        "Authorization": f"Bearer {credentials.token}",
        "v": _APP_VERSION,
        "appid": _APP_ID,
        "plat": "android",
        "lang": "EN",
        "Content-Type": "application/json",
        "ts": timestamp_ms,
    }
    url = f"{config.portal_url.rstrip('/')}{_PATH_START_WATCH}"
    async with config.session.get(
        url, params=params, headers=headers, timeout=_TIMEOUT
    ) as response:
        status = response.status
        data = orjson.loads(await response.read())

    if not isinstance(data, dict):
        msg = f"start_watch returned an invalid response (HTTP {status})"
        raise LiveViewError(msg)
    if str(data.get("ret", "")).lower() != "ok" or not isinstance(
        creds := data.get("credentials"), dict
    ):
        code = data.get("code")
        message = data.get("message") or data.get("msg")
        if code == _CODE_WRONG_PIN:
            msg = f"Wrong live view PIN: {message}"
            raise LiveViewPinError(msg)
        msg = f"start_watch failed (HTTP {status}, code={code!r}, message={message!r})"
        raise LiveViewError(msg)

    return _KinesisSession(
        region=str(data["region"]),
        channel=str(data["channel"]),
        client_id=str(data["client_id"]),
        access_key_id=str(creds["AccessKeyId"]),
        secret_access_key=str(creds["SecretAccessKey"]),
        session_token=str(creds["SessionToken"]),
    )


async def _app_ping(authenticator: Authenticator, device_info: ApiDeviceInfo) -> None:
    """Send the appping command like the app does before the stream starts."""
    service: dict[str, Any] = device_info.get("service") or {}  # type: ignore[assignment]
    if not (host := str(service.get("mqs") or "").strip()):
        return
    credentials = await authenticator.authenticate()
    service_id = _random_id(16)
    body = {
        "body": {},
        "header": {
            "channel": "Android",
            "m": "request",
            "pri": 2,
            "reqid": _random_id(6),
            "ts": str(int(time.time() * 1000)),
            "tzc": "UTC",
            "tzm": 0,
            "ver": "0.0.22",
        },
    }
    params = {
        "si": service_id,
        "ct": "m",
        "eid": device_info["did"],
        "et": device_info["class"],
        "er": device_info["resource"],
        "apn": "appping",
        "fmt": "j",
    }
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "X-ECO-REQUEST-ID": service_id,
        "Content-Type": "application/octet-stream",
        "Accept": "application/json",
    }
    async with authenticator.config.session.post(
        f"https://{host}/api/iot/endpoint/control",
        params=params,
        data=orjson.dumps(body),
        headers=headers,
        timeout=_TIMEOUT,
    ) as response:
        await response.read()
        if response.status >= 400:
            _LOGGER.debug("appping returned HTTP %s", response.status)


def _quote(value: str) -> str:
    return quote(value, safe="-_.~")


def _signing_key(secret_key: str, date_stamp: str, region: str) -> bytes:
    key = hmac.new(
        f"AWS4{secret_key}".encode(), date_stamp.encode(), hashlib.sha256
    ).digest()
    key = hmac.new(key, region.encode(), hashlib.sha256).digest()
    key = hmac.new(key, _SERVICE.encode(), hashlib.sha256).digest()
    return hmac.new(key, b"aws4_request", hashlib.sha256).digest()


def _signature(
    session: _KinesisSession, now: datetime, canonical_request: str
) -> tuple[str, str]:
    """Return the scope and the AWS SigV4 signature."""
    date_stamp = now.strftime("%Y%m%d")
    scope = f"{date_stamp}/{session.region}/{_SERVICE}/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            now.strftime("%Y%m%dT%H%M%SZ"),
            scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ]
    )
    signature = hmac.new(
        _signing_key(session.secret_access_key, date_stamp, session.region),
        string_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()
    return scope, signature


async def _aws_post(
    http: ClientSession,
    session: _KinesisSession,
    url: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    body = orjson.dumps(payload)
    parsed = urlparse(url)
    now = datetime.now(UTC)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    signed = {
        "content-type": "application/json",
        "host": parsed.netloc,
        "x-amz-date": amz_date,
        "x-amz-security-token": session.session_token,
    }
    names = sorted(signed)
    canonical_request = "\n".join(
        [
            "POST",
            parsed.path or "/",
            "",
            "".join(f"{name}:{signed[name]}\n" for name in names),
            ";".join(names),
            hashlib.sha256(body).hexdigest(),
        ]
    )
    scope, signature = _signature(session, now, canonical_request)
    headers = {
        "Content-Type": "application/json",
        "X-Amz-Date": amz_date,
        "X-Amz-Security-Token": session.session_token,
        "Authorization": (
            f"AWS4-HMAC-SHA256 Credential={session.access_key_id}/{scope}, "
            f"SignedHeaders={';'.join(names)}, Signature={signature}"
        ),
    }
    async with http.post(url, data=body, headers=headers, timeout=_TIMEOUT) as response:
        raw = await response.read()
        if response.status >= 400:
            msg = f"AWS {parsed.path} failed with HTTP {response.status}"
            raise LiveViewError(msg)
    value = orjson.loads(raw)
    if not isinstance(value, dict):
        msg = f"AWS {parsed.path} returned an invalid response"
        raise LiveViewError(msg)
    return value


def _signed_url(session: _KinesisSession, arn: str, endpoint: str) -> str:
    """Return the presigned signaling url for a viewer."""
    parsed = urlparse(endpoint)
    now = datetime.now(UTC)
    date_stamp = now.strftime("%Y%m%d")
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params.update(
        {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-ChannelARN": arn,
            "X-Amz-ClientId": session.client_id,
            "X-Amz-Credential": (
                f"{session.access_key_id}/{date_stamp}/{session.region}"
                f"/{_SERVICE}/aws4_request"
            ),
            "X-Amz-Date": now.strftime("%Y%m%dT%H%M%SZ"),
            "X-Amz-Expires": str(SIGNED_URL_VALIDITY),
            "X-Amz-Security-Token": session.session_token,
            "X-Amz-SignedHeaders": "host",
        }
    )
    query = "&".join(f"{_quote(k)}={_quote(v)}" for k, v in sorted(params.items()))
    path = parsed.path or "/"
    canonical_request = "\n".join(
        [
            "GET",
            path,
            query,
            f"host:{parsed.netloc}\n",
            "host",
            hashlib.sha256(b"").hexdigest(),
        ]
    )
    _, signature = _signature(session, now, canonical_request)
    return urlunparse(
        ("wss", parsed.netloc, path, "", f"{query}&X-Amz-Signature={signature}", "")
    )


async def _go2rtc_source(http: ClientSession, session: _KinesisSession) -> str:
    base = f"https://{_SERVICE}.{session.region}.amazonaws.com"
    channel = await _aws_post(
        http,
        session,
        f"{base}/describeSignalingChannel",
        {"ChannelName": session.channel},
    )
    arn = str(channel["ChannelInfo"]["ChannelARN"])
    endpoints = await _aws_post(
        http,
        session,
        f"{base}/getSignalingChannelEndpoint",
        {
            "ChannelARN": arn,
            "SingleMasterChannelEndpointConfiguration": {
                "Protocols": ["WSS", "HTTPS"],
                "Role": "VIEWER",
            },
        },
    )
    urls = {
        str(item["Protocol"]): str(item["ResourceEndpoint"])
        for item in endpoints.get("ResourceEndpointList", [])
    }
    ice = await _aws_post(
        http,
        session,
        f"{urls['HTTPS'].rstrip('/')}/v1/get-ice-server-config",
        {"ChannelARN": arn, "ClientId": session.client_id, "Service": "TURN"},
    )
    ice_servers: list[dict[str, Any]] = [
        {"urls": [f"stun:stun.{_SERVICE}.{session.region}.amazonaws.com:443"]}
    ]
    ice_servers.extend(
        {
            "urls": server["Uris"],
            "username": server["Username"],
            "credential": server["Password"],
        }
        for server in ice.get("IceServerList", [])
    )
    signed = _signed_url(session, arn, urls["WSS"])
    return (
        f"webrtc:{signed}#format=kinesis#client_id={session.client_id}"
        f"#ice_servers={orjson.dumps(ice_servers).decode()}"
    )


async def async_get_live_view_source(
    authenticator: Authenticator,
    device_info: ApiDeviceInfo,
    pin: str,
    pin_encoding: PinEncoding,
) -> LiveViewSource:
    """Start the camera and return the go2rtc source for the live view.

    The source must be used within SIGNED_URL_VALIDITY seconds.
    """
    session = await _start_watch(
        authenticator, device_info, encode_pin(pin, pin_encoding)
    )
    await _app_ping(authenticator, device_info)
    url = await _go2rtc_source(authenticator.config.session, session)
    return LiveViewSource(url=url, created=time.monotonic())
