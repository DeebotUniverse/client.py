"""Tests for OnMapTrace — mower variant with LZMA-compressed info field."""

from __future__ import annotations

import base64
import json as _json
import lzma

import pytest

from deebot_client.events import FirmwareEvent
from deebot_client.events.map import MapTraceEvent
from deebot_client.message import HandlingState
from deebot_client.messages.json.map import OnMapTrace
from tests.messages.json import assert_message


# ---------------------------------------------------------------------------
# Helper: encode bytes the same way mower firmware does
# ---------------------------------------------------------------------------
#
# Real GOAT A1600 RTK firmware 1.15.x emits an LZMA1 stream with a
# *trimmed* 9-byte header (props + dict_size_le + size_le_4_bytes) instead
# of the standard LZMA1 ALONE 13-byte header. The Rust helper
# ``decompress_base64_data`` accommodates this by injecting four zero
# bytes after position 7 to rebuild a valid 13-byte header. Reproduce
# that on the encoding side here so the round-trip works.

_DICT_SIZE = 1 << 18  # 256 KB — matches what real firmware advertises


def _ecovacs_encode(payload: bytes) -> str:
    raw = lzma.compress(
        payload,
        format=lzma.FORMAT_RAW,
        filters=[{"id": lzma.FILTER_LZMA1,
                  "preset": lzma.PRESET_DEFAULT,
                  "dict_size": _DICT_SIZE}],
    )
    header = bytes([0x5D]) + _DICT_SIZE.to_bytes(4, "little") + len(payload).to_bytes(4, "little")
    return base64.b64encode(header + raw).decode("ascii")


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


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_OnMapTrace_decompresses_and_flattens_groups() -> None:
    inner = '[["7","0;100,200;150,250;"]]'
    data = inner.encode("utf-8")
    info = _ecovacs_encode(data)

    expected_trace = "100,200;150,250"
    assert_message(
        OnMapTrace,
        _envelope(info, len(data)),
        (FirmwareEvent("1.15.13"), MapTraceEvent(start=1, total=1, data=expected_trace)),
        device_class="xmp9ds",
    )


def test_OnMapTrace_concatenates_multiple_groups_and_segments() -> None:
    inner = (
        '[["5","0;-11850,-28849;-11800,-28899;","0;-12850,-23699;-12800,-23750;"],'
        '["6","0;-7899,-39700;-7950,-39649;"]]'
    )
    data = inner.encode("utf-8")
    info = _ecovacs_encode(data)
    expected_trace = (
        "-11850,-28849;-11800,-28899;-12850,-23699;-12800,-23750;-7899,-39700;-7950,-39649"
    )
    assert_message(
        OnMapTrace,
        _envelope(info, len(data)),
        (FirmwareEvent("1.15.13"), MapTraceEvent(start=1, total=1, data=expected_trace)),
        device_class="xmp9ds",
    )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_OnMapTrace_no_info_field_returns_analyse() -> None:
    """Without ``info``, defer to the legacy GetMapTrace handler — analyse, no event."""
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
    """A payload with no actual coordinates is unusable — analyse rather than emit empty event."""
    inner = "[]"
    data = inner.encode("utf-8")
    info = _ecovacs_encode(data)
    assert_message(
        OnMapTrace,
        _envelope(info, len(data)),
        FirmwareEvent("1.15.13"),
        device_class="xmp9ds",
        expected_state=HandlingState.ANALYSE_LOGGED,
    )


@pytest.mark.parametrize(
    "broken_info",
    [
        "@@@not-base64@@@",                    # invalid base64
        base64.b64encode(b"too short").decode("ascii"),  # too short for LZMA header
        _ecovacs_encode(b"not json content"),  # decompresses to non-JSON
    ],
)
def test_OnMapTrace_corrupt_info_returns_analyse(broken_info: str) -> None:
    """Truncated/broken ``info`` (typical when upstream loggers truncate the payload)
    should not raise — log at debug and return analyse so the message is dropped silently.
    """
    assert_message(
        OnMapTrace,
        _envelope(broken_info, 0),
        FirmwareEvent("1.15.13"),
        device_class="xmp9ds",
        expected_state=HandlingState.ANALYSE_LOGGED,
    )


def test_OnMapTrace_uses_serial_as_event_start() -> None:
    """``serial`` becomes the ``MapTraceEvent.start`` so the Map helper does not clear
    on every push (it only clears when ``start == 0``)."""
    inner = '[["1","0;1,2;3,4;"]]'
    data = inner.encode("utf-8")
    info = _ecovacs_encode(data)
    envelope = _envelope(info, len(data))
    envelope["body"]["data"]["serial"] = "42"

    assert_message(
        OnMapTrace,
        envelope,
        (FirmwareEvent("1.15.13"), MapTraceEvent(start=42, total=42, data="1,2;3,4")),
        device_class="xmp9ds",
    )
