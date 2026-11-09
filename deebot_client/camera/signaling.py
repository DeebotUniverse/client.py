"""KVS WebRTC signaling utilities for Ecovacs robots.

Provides two categories of helpers used during the WebRTC handshake between
Home Assistant (VIEWER) and the robot (MASTER):

**AWS SigV4 URL signing** — ``sign_wss_url``
    KVS uses standard AWS Signature Version 4 to authenticate the WebSocket
    upgrade request.  This function constructs the canonical request, derives
    the signing key using HMAC-SHA256 chains, and appends the signature and all
    required ``X-Amz-*`` query parameters to the WSS endpoint URL returned by
    ``start_watch_v2``.  No AWS SDK is needed; the algorithm is implemented
    here in pure Python (``hashlib`` + ``hmac``).

**KVS WebSocket message builders** — ``make_sdp_offer_msg``, ``make_ice_msg``
    The KVS signaling protocol wraps WebRTC SDP and ICE payloads in a simple
    JSON envelope with a base64-encoded ``messagePayload``.  These helpers
    produce the ``SDP_OFFER`` and ``ICE_CANDIDATE`` messages that the VIEWER
    sends to the MASTER over the signed WebSocket connection.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime
import hashlib
import hmac
import urllib.parse

import orjson


def _b64(data: str | bytes) -> str:
    """Encode a string or bytes value as base64."""
    if isinstance(data, str):
        data = data.encode()
    return base64.b64encode(data).decode()


def sign_wss_url(
    wss_endpoint: str,
    channel_arn: str,
    client_id: str,
    creds: dict[str, str],
    region: str,
) -> str:
    """Sign a KVS WebSocket URL using AWS Signature Version 4 (VIEWER role).

    The signing procedure follows the standard AWS SigV4 algorithm:
    1. Build a canonical query string that includes all ``X-Amz-*`` parameters
       sorted lexicographically.
    2. Construct the canonical request (HTTP method, URI, query string,
       canonical headers, payload hash).
    3. Derive the signing key through a chain of four HMAC-SHA256 operations:
       ``DateKey → DateRegionKey → DateRegionServiceKey → SigningKey``.
    4. Compute the final signature and append ``X-Amz-Signature`` to the URL.

    The ``X-Amz-ClientId`` parameter identifies this viewer connection to the
    KVS signaling channel and must match the ``clientId`` returned by
    ``start_watch_v2``.

    Args:
        wss_endpoint: The base WSS URL from ``start_watch_v2`` (e.g.
            ``wss://m-a1b2c3d4e5f6.kinesisvideo.eu-west-1.amazonaws.com``).
        channel_arn: The KVS channel ARN from ``start_watch_v2``.
        client_id: The viewer client ID from ``start_watch_v2``.
        creds: A dict with ``AccessKeyId``, ``SecretAccessKey``, and
            optionally ``SessionToken`` (from the temporary STS credentials
            returned by ``start_watch_v2``).
        region: AWS region string (e.g. ``"eu-west-1"``).

    Returns:
        A fully-signed ``wss://`` URL ready for use with a WebSocket client.
    """
    host = wss_endpoint.replace("wss://", "").split("/")[0]
    now = datetime.now(UTC)
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%Y%m%dT%H%M%SZ")
    service = "kinesisvideo"

    qs_params: dict[str, str] = {
        "X-Amz-ChannelARN": channel_arn,
        "X-Amz-ClientId": client_id,
        "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
        "X-Amz-Credential": (
            f"{creds['AccessKeyId']}/{date_str}/{region}/{service}/aws4_request"
        ),
        "X-Amz-Date": time_str,
        "X-Amz-Expires": "299",
        "X-Amz-SignedHeaders": "host",
    }
    if creds.get("SessionToken"):
        qs_params["X-Amz-Security-Token"] = creds["SessionToken"]

    def _url_encode(s: str) -> str:
        return urllib.parse.quote(s, safe="")

    sorted_qs = "&".join(
        f"{_url_encode(k)}={_url_encode(v)}" for k, v in sorted(qs_params.items())
    )

    canonical_req = "\n".join(
        [
            "GET",
            "/",
            sorted_qs,
            f"host:{host}\n",
            "host",
            # Empty payload hash (GET request with no body)
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        ]
    )
    scope = f"{date_str}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            time_str,
            scope,
            hashlib.sha256(canonical_req.encode()).hexdigest(),
        ]
    )

    def _hmac_sha256(key: bytes | str, msg: str) -> bytes:
        if isinstance(key, str):
            key = key.encode()
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()

    signing_key = _hmac_sha256(
        _hmac_sha256(
            _hmac_sha256(
                _hmac_sha256(f"AWS4{creds['SecretAccessKey']}", date_str),
                region,
            ),
            service,
        ),
        "aws4_request",
    )
    signature = _hmac_sha256(signing_key, string_to_sign).hex()
    qs_params["X-Amz-Signature"] = signature
    final_qs = "&".join(
        f"{_url_encode(k)}={_url_encode(v)}" for k, v in sorted(qs_params.items())
    )
    return f"wss://{host}/?{final_qs}"


def make_sdp_offer_msg(sdp: str, client_id: str) -> bytes:
    """Build a KVS WebSocket ``SDP_OFFER`` message.

    The ``messagePayload`` field is base64-encoded JSON containing the SDP
    offer string and type identifier, as required by the KVS signaling
    protocol.

    Args:
        sdp: The SDP offer string produced by the local WebRTC peer connection.
        client_id: The viewer client ID to include as ``senderClientId``.

    Returns:
        JSON-encoded bytes ready to send over the KVS signaling WebSocket.
    """
    return orjson.dumps(
        {
            "action": "SDP_OFFER",
            "recipientClientId": "",
            "messagePayload": _b64(
                orjson.dumps({"type": "offer", "sdp": sdp}).decode()
            ),
            "senderClientId": client_id,
        }
    )


def make_ice_msg(
    candidate: str, sdp_mid: str, sdp_mline: int, client_id: str
) -> bytes:
    """Build a KVS WebSocket ``ICE_CANDIDATE`` message.

    Encodes an ICE candidate (obtained from the local WebRTC peer connection
    ``on_icecandidate`` callback) in the KVS signaling wire format.

    Args:
        candidate: The ICE candidate string (e.g. ``"candidate:…"``).
        sdp_mid: The media stream ID associated with the candidate.
        sdp_mline: The zero-based media description index (``sdpMLineIndex``).
        client_id: The viewer client ID to include as ``senderClientId``.

    Returns:
        JSON-encoded bytes ready to send over the KVS signaling WebSocket.
    """
    return orjson.dumps(
        {
            "action": "ICE_CANDIDATE",
            "recipientClientId": "",
            "messagePayload": _b64(
                orjson.dumps(
                    {
                        "candidate": candidate,
                        "sdpMid": sdp_mid,
                        "sdpMLineIndex": sdp_mline,
                    }
                ).decode()
            ),
            "senderClientId": client_id,
        }
    )
