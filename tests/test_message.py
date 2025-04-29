from __future__ import annotations

from unittest.mock import Mock

import pytest

from deebot_client.event_bus import EventBus
from deebot_client.message import (
    HandlingResult,
    HandlingState,
    Message,
    MessagePayloadType,
    MessageStr,
)


class WronglyImplementedMessage(Message):
    """Mock class of a wrongly implemented message."""

    NAME = "WronglyImplementedMessage"


class TestMessageStr(MessageStr):
    """Mock class for MessageStr."""

    NAME = "TestMessageStr"

    @classmethod
    def _handle_str(cls, _event_bus: EventBus, message: str) -> HandlingResult:
        assert isinstance(message, str)
        return HandlingResult(HandlingState.SUCCESS, {"payload": message})


@pytest.mark.parametrize(
    ("input", "expected"),
    [
        ("a string", "a string"),
        (b"a byte string", "a byte string"),
        (bytearray(b"a byte array string"), "a byte array string"),
    ],
    ids=["string", "byte string", "byte array"],
)
def test_MessageStr_should_convert_across_types(
    input: MessagePayloadType, expected: str
) -> None:
    event_bus = Mock(spec_set=EventBus)
    result = TestMessageStr.handle(event_bus, input)

    assert result.state == HandlingState.SUCCESS

    assert result.args is not None

    converted = result.args.get("payload")
    assert converted is not None
    assert converted == expected


def test_MessageStr_should_error_on_unknown_types() -> None:
    event_bus = Mock(spec_set=EventBus)
    result = TestMessageStr.handle(event_bus, {"key": "value"})

    assert result.state == HandlingState.ERROR


def test_WronglyImplementedMessage() -> None:
    event_bus = Mock(spec_set=EventBus)
    result = WronglyImplementedMessage.handle(event_bus, {})

    assert result.state == HandlingState.ERROR
