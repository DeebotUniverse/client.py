"""Tests for OnMapTrace — mower variant with LZMA-compressed info field."""

from __future__ import annotations

import pytest

from deebot_client.events import FirmwareEvent
from deebot_client.events.map import MapTraceEvent
from deebot_client.message import HandlingState
from deebot_client.messages.json.map import OnMapTrace
from tests.messages.json import assert_message

# Static pre-encoded payloads (LZMA1 with trimmed header, base64).
# Generated from real GOAT A1600 RTK firmware 1.15.x encoding format.

# '[["7","0;100,200;150,250;"]]' (28 bytes uncompressed)
_SINGLE_GROUP = "XQAABAAcAAAAAC3ghG4jMKGNRtkww/d7MLX33z8usOwaHU2B7///wFIAAA=="

# '[["5","0;-11850,-28849;-11800,-28899;","0;-12850,-23699;-12800,-23750;"],["6","0;-7899,-39700;-7950,-39649;"]]' (110 bytes)
_MULTI_GROUP = "XQAABABuAAAAAC3ghGojMKGNRtiHVVsAoT/QJyYK0+w8iNNfkK1fJciMh2LrturUwS3TNs8H+7FN7dV1zViWeRKpxrkDUNNQG/4bayp4L33u+jJYgA=="

# '[]' (2 bytes)
_EMPTY_GROUPS = "XQAABAACAAAAAC2XXP/////wAAAA"

# '[["1","0;1,2;3,4;"]]' (20 bytes)
_SERIAL_TEST = "XQAABAAUAAAAAC3ghGIjMKGNR5N7rKaBA7QSJbYEb82/P//2SwAA"

# b'not json content' compressed — decompresses to non-JSON
_NON_JSON = "XQAABAAQAAAAADcbyuolm7SQrGkrEp4K2Iwi8deA//3qYAA="


def _envelope(info_b64: str, info_size: int, fw: str = "1.15.13") -> dict:
    return {
        "header": {
            "pri": 1,
            "tzm": 120,
            "ts": "1777450352860644879",
            "fwVer": fw,
            "hwVer": "0.0.0",
        },
        "body": {
            "data": {
                "mid": "123456789",
                "batid": "hmfald",
                "serial": "1",
                "index": "0",
                "type": "4",
                "info": info_b64,
                "infoSize": info_size,
            }
        },
    }


def test_OnMapTrace_decompresses_and_flattens_groups() -> None:
    assert_message(
        OnMapTrace,
        _envelope(_SINGLE_GROUP, 28),
        (FirmwareEvent("1.15.13"), MapTraceEvent(start=1, total=1, data="100,200;150,250")),
        device_class="xmp9ds",
    )


def test_OnMapTrace_concatenates_multiple_groups_and_segments() -> None:
    expected_trace = (
        "-11850,-28849;-11800,-28899;-12850,-23699;-12800,-23750;-7899,-39700;-7950,-39649"
    )
    assert_message(
        OnMapTrace,
        _envelope(_MULTI_GROUP, 110),
        (FirmwareEvent("1.15.13"), MapTraceEvent(start=1, total=1, data=expected_trace)),
        device_class="xmp9ds",
    )


def test_OnMapTrace_no_info_field_returns_analyse() -> None:
    envelope = _envelope("", 0)
    envelope["body"]["data"].pop("info")
    envelope["body"]["data"].pop("infoSize")
    assert_message(
        OnMapTrace,
        envelope,
        FirmwareEvent("1.15.13"),
        device_class="xmp9ds",
        expected_state=HandlingState.ANALYSE_LOGGED,
    )


def test_OnMapTrace_empty_groups_returns_analyse() -> None:
    assert_message(
        OnMapTrace,
        _envelope(_EMPTY_GROUPS, 2),
        FirmwareEvent("1.15.13"),
        device_class="xmp9ds",
        expected_state=HandlingState.ANALYSE_LOGGED,
    )


@pytest.mark.parametrize(
    "broken_info",
    [
        "@@@not-base64@@@",
        "AQIDBA==",  # too short for LZMA header
        _NON_JSON,
    ],
)
def test_OnMapTrace_corrupt_info_returns_analyse(broken_info: str) -> None:
    assert_message(
        OnMapTrace,
        _envelope(broken_info, 0),
        FirmwareEvent("1.15.13"),
        device_class="xmp9ds",
        expected_state=HandlingState.ANALYSE_LOGGED,
    )


def test_OnMapTrace_uses_serial_as_event_start() -> None:
    envelope = _envelope(_SERIAL_TEST, 20)
    envelope["body"]["data"]["serial"] = "42"

    assert_message(
        OnMapTrace,
        envelope,
        (FirmwareEvent("1.15.13"), MapTraceEvent(start=42, total=42, data="1,2;3,4")),
        device_class="xmp9ds",
    )
