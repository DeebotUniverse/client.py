"""Tests for the evidenced GOAT onMI static-map representation."""

from __future__ import annotations

import base64
import hashlib
import lzma
from pathlib import Path
from typing import TYPE_CHECKING, Any

import orjson
import pytest

from deebot_client.events import FirmwareEvent, MowerStaticMapEvent
from deebot_client.message import HandlingState
from deebot_client.messages.json.map import OnMI
import deebot_client.messages.json.map.on_mi as on_mi_module
from deebot_client.messages.json.map.on_mi import _strict_base64_decode

if TYPE_CHECKING:
    from unittest.mock import Mock

_FIXTURE_PATH = (
    Path(__file__).parents[3]
    / "fixtures"
    / "goat_map"
    / "onmi_info_representations.json"
)
_FIXTURES = {item["label"]: item for item in orjson.loads(_FIXTURE_PATH.read_bytes())}
_REQUEST = _FIXTURES["request-876"]
_CADENCE = _FIXTURES["cadence-52"]

# Static, repository-safe malformed/unknown representations. They are kept
# pre-encoded so tests do not manufacture production-like payloads at runtime.
_UNKNOWN_RECORD_INFO = "XQAAgAAeAAAAAC3ghGIjMKGd8ITHsUgK6Vw3ll4JieU8lR0E9Uj79v7UNQA="
_UNKNOWN_EXTRA_RECORD_INFO = (
    "XQAAgAAuAAAAAC3ghGIjMKGaFgup/eUb9NwOBpiwD8q85blr9F+lf3ruZphhXH3BKjN+4ek6X//z0p8A"
)
_UNSUPPORTED_RLE_INFO = (
    "XQAAgAAeAAAAAC3ghGIjMKGc3GOvIQQK5rv3N9eXRvwO/U7Av5Jxnit//8vj0AA="
)
_MALFORMED_JSON_INFO = "XQAABACvAAAAAAAAAEINQkt4BfqEvt9Pow7YU9KWRVBcSBosIDAOtACCicHy+vmfexxcutQUhqkAPQlBawOeXo/VSrOqF7yhdJ1JPICUs3IhIebU62Qego0vdk8oObiLh3VY/PVkqQyvR4dHxUDzMhX7HAguZVn3yC17+cQ18N4kaydN3LfSUtV/zejrBM4="
_DECOMPRESSION_FAILURE_INFO = "XQAABAAHAAAAAA=="


def _message(
    *,
    info: str | None = None,
    info_size: object = None,
    index: object = "0",
    mid: object = "1",
) -> dict[str, Any]:
    if info is None:
        info = _REQUEST["original"]
    if info_size is None:
        info_size = _REQUEST["info_size"]
    return {
        "header": {"fwVer": "1.9.16"},
        "body": {
            "data": {
                "mid": mid,
                "batid": "excluded-from-event",
                "serial": "1",
                "index": index,
                "using": 1,
                "type": "0",
                "info": info,
                "infoSize": info_size,
            }
        },
    }


def _synthetic_info(document: object) -> tuple[str, int]:
    """Encode a small valid trimmed LZMA representation for branch tests."""
    payload = orjson.dumps(document)
    compressed = bytearray(
        lzma.compress(
            payload,
            format=lzma.FORMAT_ALONE,
            filters=[
                {
                    "id": lzma.FILTER_LZMA1,
                    "dict_size": 262_144,
                    "lc": 3,
                    "lp": 0,
                    "pb": 2,
                }
            ],
        )
    )
    compressed[5:13] = len(payload).to_bytes(8, "little")
    trimmed = compressed[:9] + compressed[13:]
    return base64.b64encode(trimmed).decode("ascii"), len(payload)


@pytest.mark.parametrize("fixture", [_REQUEST, _CADENCE], ids=["request", "cadence"])
def test_onMI_golden_representation_integrity(fixture: dict[str, Any]) -> None:
    original = fixture["original"].encode("ascii")

    assert len(original) == fixture["original_byte_length"]
    assert hashlib.sha256(original).hexdigest() == fixture["original_sha256"]
    assert _strict_base64_decode(fixture["original"]) is not None


@pytest.mark.parametrize("index", [0, "0"])
@pytest.mark.parametrize("info_size", [1756, "1756"])
def test_onMI_decodes_o1200_static_geometry_exactly(
    event_bus_mock: Mock, index: int | str, info_size: int | str
) -> None:
    result = OnMI.handle(event_bus_mock, _message(index=index, info_size=info_size))

    assert result.state == HandlingState.SUCCESS
    events = [call.args[0] for call in event_bus_mock.notify.call_args_list]
    assert events[0] == FirmwareEvent("1.9.16")
    event = events[1]
    assert isinstance(event, MowerStaticMapEvent)
    assert event.mid == "1"
    assert event.step_size == 50
    assert len(event.groups) == 1
    assert event.groups[0].group_id == "1"
    assert len(event.groups[0].segments) == 1

    segment = event.groups[0].segments[0]
    assert segment.raw is not None
    assert segment.raw.startswith("s1;1;-4500,-650;")
    assert len(segment.points) == 2336
    assert segment.points[0] == (-4500, -650)
    assert segment.points[1000] == (-20650, 4050)
    assert segment.points[2000] == (3050, -16950)
    assert segment.points[-1] == (-4400, -650)
    assert min(x for x, _ in segment.points) == -34350
    assert max(x for x, _ in segment.points) == 5750
    assert min(y for _, y in segment.points) == -24350
    assert max(y for _, y in segment.points) == 21350

    # Digest of the complete point sequence exported by the independent O1200
    # reference viewer, not a second execution of this parser.
    assert hashlib.sha256(orjson.dumps(segment.points)).hexdigest() == (
        "912d2a56b7ad39a23708c548838ba47c3db6e37b8d13376b97fb6effad9c8217"
    )

    # Preserve the observed open endpoint gap; do not close it synthetically.
    assert segment.points[-1] != segment.points[0]
    assert (
        segment.points[-1][0] - segment.points[0][0],
        segment.points[-1][1] - segment.points[0][1],
    ) == (100, 0)

    # No device/account/session fields are exposed by the domain event.
    assert not hasattr(event, "batid")
    assert not hasattr(event, "source")


def test_onMI_cadence_form_is_explicitly_non_geometry(event_bus_mock: Mock) -> None:
    result = OnMI.handle(
        event_bus_mock,
        _message(info=_CADENCE["original"], info_size=_CADENCE["info_size"]),
    )

    assert result.state == HandlingState.ANALYSE_LOGGED
    assert event_bus_mock.notify.call_count == 1


def test_onMI_base64_layer_requires_canonical_representation() -> None:
    with pytest.raises(ValueError, match="not canonical"):
        _strict_base64_decode("AB==")


@pytest.mark.parametrize(
    ("info", "info_size"),
    [
        ("not-base64", 1),
        ("XQA=", 1),
        ("AAAAAAAHAQAAAA==", 7),
        (_DECOMPRESSION_FAILURE_INFO, 7),
        (_MALFORMED_JSON_INFO, 175),
        (_UNKNOWN_RECORD_INFO, 30),
        (_UNKNOWN_EXTRA_RECORD_INFO, 46),
        (_UNSUPPORTED_RLE_INFO, 30),
    ],
    ids=[
        "invalid-base64",
        "short-lzma-header",
        "wrong-lzma-prefix",
        "decompression-failure",
        "malformed-json",
        "unknown-segment",
        "unknown-group-shape",
        "unsupported-rle-token",
    ],
)
def test_onMI_unknown_or_invalid_structures_fail_closed(
    event_bus_mock: Mock, info: str, info_size: int
) -> None:
    result = OnMI.handle(event_bus_mock, _message(info=info, info_size=info_size))

    assert result.state == HandlingState.ANALYSE_LOGGED
    assert event_bus_mock.notify.call_count == 1


def test_onMI_rejects_wrong_info_size(event_bus_mock: Mock) -> None:
    result = OnMI.handle(event_bus_mock, _message(info_size=1755))

    assert result.state == HandlingState.ANALYSE_LOGGED
    assert event_bus_mock.notify.call_count == 1


@pytest.mark.parametrize("index", ["00", "1", 1, True, None])
def test_onMI_requires_canonical_first_index(
    event_bus_mock: Mock, index: object
) -> None:
    result = OnMI.handle(event_bus_mock, _message(index=index))

    assert result.state == HandlingState.ANALYSE_LOGGED
    assert event_bus_mock.notify.call_count == 1


def test_onMI_requires_inner_map_id_to_match_envelope(event_bus_mock: Mock) -> None:
    result = OnMI.handle(event_bus_mock, _message(mid="2"))

    assert result.state == HandlingState.ANALYSE_LOGGED
    assert event_bus_mock.notify.call_count == 1


@pytest.mark.parametrize("mid", [None, "", 1])
def test_onMI_requires_nonempty_string_mid(event_bus_mock: Mock, mid: object) -> None:
    result = OnMI.handle(event_bus_mock, _message(mid=mid))

    assert result.state == HandlingState.ANALYSE_LOGGED
    assert event_bus_mock.notify.call_count == 1


@pytest.mark.parametrize("info_size", [None, 0, -1, "00", True])
def test_onMI_requires_positive_canonical_info_size(
    event_bus_mock: Mock, info_size: object
) -> None:
    message = _message()
    message["body"]["data"]["infoSize"] = info_size
    result = OnMI.handle(event_bus_mock, message)

    assert result.state == HandlingState.ANALYSE_LOGGED
    assert event_bus_mock.notify.call_count == 1


@pytest.mark.parametrize("info", [None, 123, ["not-a-string"]])
def test_onMI_requires_string_info(event_bus_mock: Mock, info: object) -> None:
    message = _message()
    message["body"]["data"]["info"] = info
    result = OnMI.handle(event_bus_mock, message)

    assert result.state == HandlingState.ANALYSE_LOGGED
    assert event_bus_mock.notify.call_count == 1


@pytest.mark.parametrize(
    "document",
    [
        {"not": "a list"},
        [["1"], ["2", "0"]],
        [["1", "not-a-record"], ["2", "0"]],
        [["1", "s1;1;bad;1"], ["2", "0"]],
        [["1", "s1;1;0,0;1 3"], ["2", "0"]],
        [["1", "s1;1;0,0;1(100000)"], ["2", "0"]],
        [["1", "s1;1;0,0;?"], ["2", "0"]],
    ],
    ids=[
        "decoded-payload-not-list",
        "record-shape",
        "malformed-segment",
        "invalid-coordinate",
        "rle-gap",
        "point-safety-cap",
        "empty-point-expansion",
    ],
)
def test_onMI_synthetic_fail_closed_branches(
    event_bus_mock: Mock, document: object
) -> None:
    info, info_size = _synthetic_info(document)
    result = OnMI.handle(event_bus_mock, _message(info=info, info_size=info_size))

    assert result.state == HandlingState.ANALYSE_LOGGED
    assert event_bus_mock.notify.call_count == 1


def test_onMI_rejects_decoder_length_mismatch(
    event_bus_mock: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    info, info_size = _synthetic_info([["1", "s1;1;0,0;1"], ["2", "0"]])
    monkeypatch.setattr(
        on_mi_module,
        "decode_trimmed_lzma",
        lambda _value, *, _info_size: b"{}",
    )

    result = OnMI.handle(event_bus_mock, _message(info=info, info_size=info_size))

    assert result.state == HandlingState.ANALYSE_LOGGED
    assert event_bus_mock.notify.call_count == 1
