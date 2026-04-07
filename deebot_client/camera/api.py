"""KVS camera HTTP API client for Ecovacs robots.

This module handles all HTTP interactions with the Ecovacs cloud required to
establish and terminate a KVS (AWS Kinesis Video Streams) WebRTC camera session:

- ``start_watch_v2`` — authenticates with the Ecovacs API and returns the AWS
  credentials, KVS channel ARN, ICE server config, and a session-ID that must
  be presented to ``end_watch`` when the stream is closed.
- ``end_watch`` — cleanly terminates the cloud-side session so the robot stops
  streaming and the channel can be reused by another viewer.
- ``verify_video_pwd`` — validates the numeric camera PIN before starting a
  session; robots with a PIN lock reject ``start_watch_v2`` with a specific
  error code if the PIN has not been verified first.
- ``encode_pin`` / ``generate_video_track_id`` — small helpers shared between
  the API layer and the HA integration options flow.

The module also contains two thin wrappers — ``send_video_opened`` and
``set_audio_call_state`` — that publish the MQTT P2P messages the robot needs
in order to open its video encoder and properly track viewer presence.

The API gateway URL is continent-scoped (``eu``, ``na``, ``ww``).  All calls
use standard Ecovacs V3 request headers including a timestamp-based HMAC-SHA1
signature that prevents replay attacks.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import logging
import random
import string
import time
from typing import Any, cast
import uuid

import orjson
from aiohttp import ClientSession, ClientTimeout

_LOGGER = logging.getLogger(__name__)

# API gateway for KVS session control.
# Different from the portal URL used by deebot-client for GetDeviceList.
# The datacenter segment (eu / na / ww) must match the user's continent.
_MA_GW_TEMPLATE = "https://api-app.dc-{continent}.ww.ecouser.net"


def get_ma_gw(continent: str) -> str:
    """Return the KVS API gateway URL for the given continent (eu / na / ww)."""
    return _MA_GW_TEMPLATE.format(continent=continent)


_APP_VERSION = "2.1.0"
_APP_VERSION_HEADER = "3.12.0"
_APP_PLATFORM = "android"
_APP_PLATFORM_PARAMS = "Android"
_APP_LANG = "en"

# PIN encoding: MD5("eco_" + pin_digits)
PIN_PREFIX = "eco_"

_TRACK_ID_CHARS = string.ascii_letters + string.digits


def encode_pin(pin_digits: str) -> str:
    """Encode the camera PIN as MD5(PIN_PREFIX + pin_digits)."""
    return hashlib.md5((PIN_PREFIX + pin_digits).encode()).hexdigest()  # noqa: S324


def generate_video_track_id() -> str:
    """Generate a random 10-character alphanumeric video track ID."""
    return "".join(random.choices(_TRACK_ID_CHARS, k=10))  # noqa: S311


def _sign(ts_ms: str) -> str:
    """Compute request signature as SHA1(shared_secret + timestamp_ms)."""
    return hashlib.sha1(  # noqa: S324
        ("ecovacs2ea31cf06e6711eaa0aff7b9558a534e" + ts_ms).encode()
    ).hexdigest()


def _make_headers(token: str, user_id: str, country: str) -> dict[str, str]:
    """Build standard HTTP request headers for Ecovacs API calls."""
    ts = str(int(time.time() * 1000))
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "appid": "ecovacs",
        "plat": _APP_PLATFORM,
        "ts": ts,
        "country": country,
        "lang": _APP_LANG,
        "ucid": "",
        "v": _APP_VERSION_HEADER,
        "sign": _sign(ts),
        "token": token,
        "Authorization": f"Bearer {token}",
        "userid": user_id,
    }


async def verify_video_pwd(
    session: ClientSession,
    *,
    token: str,
    user_id: str,
    did: str,
    pin_hash: str,
    country: str,
    ma_gw: str = "",
) -> dict[str, Any]:
    """Verify the camera PIN before initiating a stream.

    POST /api/appsvr/video/pwd/verify

    Returns the raw JSON response dict.  The caller should check
    ``data["ret"] == "ok"`` before proceeding.
    """
    if not ma_gw:
        ma_gw = get_ma_gw("ww")
    url = f"{ma_gw}/api/appsvr/video/pwd/verify"
    body = orjson.dumps({"did": did, "pwd": pin_hash})
    async with session.post(
        url,
        data=body,
        headers=_make_headers(token, user_id, country),
        timeout=ClientTimeout(total=10),
    ) as resp:
        raw = await resp.read()
        try:
            data = orjson.loads(raw)
        except orjson.JSONDecodeError:
            data = {"raw": raw.decode(errors="replace")}
    _LOGGER.debug("verify_video_pwd ret=%s code=%s", data.get("ret"), data.get("code"))
    return cast("dict[str, Any]", data)


async def start_watch_v2(
    session: ClientSession,
    *,
    token: str,
    user_id: str,
    did: str,
    mid: str,
    res: str,
    pin_hash: str,
    video_track_id: str | None = None,
    country: str,
    ma_gw: str = "",
) -> dict[str, Any]:
    """Initiate a KVS video session for the robot.

    GET /api/appsvr/akvs/start_watch/v2

    On success the response contains:

    - ``channelArn`` — the KVS signaling channel ARN.
    - ``region`` — AWS region where the channel lives.
    - ``credentials`` — temporary ``AccessKeyId``, ``SecretAccessKey``,
      ``SessionToken`` for signing the WebSocket URL.
    - ``iceServerList`` — STUN/TURN servers for ICE negotiation.
    - ``clientId`` — the viewer client ID to embed in all signaling messages.
    - ``session`` — opaque session ID for ``end_watch``.
    """
    if not ma_gw:
        ma_gw = get_ma_gw("ww")
    if video_track_id is None:
        video_track_id = generate_video_track_id()

    params = {
        "videoTrackId": video_track_id,
        "lang": _APP_LANG,
        "plat": _APP_PLATFORM_PARAMS,
        "av": _APP_VERSION,
        "did": did,
        "mid": mid,
        "res": res,
        "pwd": pin_hash,
    }

    async with session.get(
        f"{ma_gw}/api/appsvr/akvs/start_watch/v2",
        params=params,
        headers=_make_headers(token, user_id, country),
        timeout=ClientTimeout(total=20),
    ) as resp:
        raw = await resp.read()
        try:
            data = orjson.loads(raw)
        except orjson.JSONDecodeError:
            data = {"raw": raw.decode(errors="replace")}
        _LOGGER.debug(
            "start_watch_v2 ret=%s session=%s", data.get("ret"), data.get("session")
        )
    return cast("dict[str, Any]", data)


async def end_watch(
    session: ClientSession,
    *,
    token: str,
    user_id: str,
    session_id: str,
    video_track_id: str,
    country: str,
    ma_gw: str = "",
) -> None:
    """Terminate the video session server-side.

    GET /api/appsvr/akvs/end_watch

    Best-effort: failures are logged as warnings and swallowed so that camera
    teardown never blocks Home Assistant entity unloading.
    """
    if not ma_gw:
        ma_gw = get_ma_gw("ww")
    params = {
        "videoTrackId": video_track_id,
        "lang": _APP_LANG,
        "plat": _APP_PLATFORM_PARAMS,
        "av": _APP_VERSION,
        "sid": session_id,
    }
    try:
        async with session.get(
            f"{ma_gw}/api/appsvr/akvs/end_watch",
            params=params,
            headers=_make_headers(token, user_id, country),
            timeout=ClientTimeout(total=10),
        ) as resp:
            _LOGGER.debug("end_watch HTTP %d", resp.status)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("End_watch failed: %s", err)


async def send_video_opened(
    *,
    enqueue_publish: Any,
    token: str,
    user_id: str,
    user_resource: str,
    did: str,
    mid: str,
    res: str,
) -> None:
    """Notify the robot via MQTT that the viewer is ready to receive video.

    The robot will not start encoding until it receives this P2P message on
    the JMQ broker.  It must be sent *after* the WebRTC offer/answer exchange
    completes and the ICE connection is established.
    """
    await _send_p2p_mqtt_cmd(
        enqueue_publish=enqueue_publish,
        token=token,
        user_id=user_id,
        user_resource=user_resource,
        did=did,
        mid=mid,
        res=res,
        cmd_name="videoOpened",
        cmd_data=None,
    )


async def set_audio_call_state(
    *,
    enqueue_publish: Any,
    token: str,
    user_id: str,
    user_resource: str,
    did: str,
    mid: str,
    res: str,
    client_id: str,
    state: int,
) -> None:
    """Send ``setAudioCallState`` to the robot via MQTT.

    ``state=1`` signals that a viewer has connected; ``state=0`` that the last
    viewer has disconnected.  The robot uses this to manage its streaming
    encoder lifecycle.
    """
    await _send_p2p_mqtt_cmd(
        enqueue_publish=enqueue_publish,
        token=token,
        user_id=user_id,
        user_resource=user_resource,
        did=did,
        mid=mid,
        res=res,
        cmd_name="setAudioCallState",
        cmd_data={"clientId": client_id, "state": state},
    )


async def _send_p2p_mqtt_cmd(
    *,
    enqueue_publish: Any,
    token: str,
    user_id: str,
    user_resource: str,
    did: str,
    mid: str,
    res: str,
    cmd_name: str,
    cmd_data: dict[str, Any] | None,
) -> None:
    """Publish a P2P MQTT command to the robot on the KVS JMQ broker.

    The topic follows the Ecovacs P2P routing scheme:
    ``iot/p2p/{cmd}/{from_uid}/{from_class}/{from_res}/{to_did}/{to_mid}/{to_res}/q/{req_id}/j``

    The payload is a JSON-encoded header/body envelope compatible with the
    Ecovacs MQTT protocol version 0.0.22.
    """
    req_id = uuid.uuid4().hex[:8]
    ts = str(int(time.time() * 1000))
    tz_offset = int(
        (
            _dt.datetime.now(_dt.UTC).astimezone().utcoffset() or _dt.timedelta()
        ).total_seconds()
        / 60
    )

    payload = orjson.dumps(
        {
            "header": {"pri": 2, "ts": ts, "tzm": tz_offset, "ver": "0.0.22"},
            "body": {"data": cmd_data},
        }
    )
    topic = (
        f"iot/p2p/{cmd_name}/{user_id}/ecouser/{user_resource}"
        f"/{did}/{mid}/{res}/q/{req_id}/j"
    )
    _LOGGER.debug("MQTT P2P %s topic=%s", cmd_name, topic)
    await enqueue_publish(topic, payload, qos=0)
