from __future__ import annotations

import logging
from unittest.mock import Mock

import pytest

from deebot_client import message as message_module
from deebot_client.event_bus import EventBus
from deebot_client.message import (
    _PARSE_FAILURE_THRESHOLD,
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
    ("value", "expected"),
    [
        ("a string", "a string"),
        (b"a byte string", "a byte string"),
        (bytearray(b"a byte array string"), "a byte array string"),
    ],
    ids=["string", "byte string", "byte array"],
)
def test_MessageStr_should_convert_across_types(
    value: MessagePayloadType, expected: str
) -> None:
    event_bus = Mock(spec_set=EventBus)
    result = TestMessageStr.handle(event_bus, value)

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


class _AlwaysRaisingMessage(Message):
    """Mock message whose ``_handle`` always raises, to exercise warn-once.

    Direct subclass of ``Message`` (not ``MessageStr``) so only the outer
    ``handle`` decorator is in play — the rate-limit count increments
    once per public ``handle()`` call instead of twice (which would happen
    via the nested ``MessageStr.__handle_str`` decorator).
    """

    NAME = "AlwaysRaisingMessage_warnonce_test"

    @classmethod
    def _handle(
        cls, _event_bus: EventBus, _message: MessagePayloadType
    ) -> HandlingResult:
        raise ValueError("simulated parse failure")


def test_warn_once_throttles_repeated_parse_failures(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """After ``_PARSE_FAILURE_THRESHOLD`` warnings, subsequent failures log at DEBUG.

    Without this rate-limit, a firmware push storm (e.g. mower map traces with
    a schema the lib does not know) was observed to produce >200 000 identical
    WARNING entries in 3 days. The first few are still useful; the rest belong
    in DEBUG so the rest of HA's log stays readable.
    """
    name = _AlwaysRaisingMessage.NAME

    # Reset state so this test is order-independent
    message_module._parse_failure_counts.pop(name, None)

    event_bus = Mock(spec_set=EventBus)
    extra_calls = 2

    with caplog.at_level(logging.DEBUG, logger="deebot_client.message"):
        for i in range(_PARSE_FAILURE_THRESHOLD + extra_calls):
            result = _AlwaysRaisingMessage.handle(event_bus, {"i": i})
            assert result.state == HandlingState.ERROR

    by_level: dict[str, list[logging.LogRecord]] = {"WARNING": [], "DEBUG": []}
    for r in caplog.records:
        if name in r.getMessage() and r.levelname in by_level:
            by_level[r.levelname].append(r)

    # First N raw warnings + 1 "switching to DEBUG" notice
    assert len(by_level["WARNING"]) == _PARSE_FAILURE_THRESHOLD + 1
    # Then ``extra_calls`` more failures fell through to DEBUG
    assert len(by_level["DEBUG"]) == extra_calls


def test_warn_once_isolated_per_message_name(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Counter is per message NAME — failures in one class don't silence another."""

    class _OtherFailingMessage(Message):
        NAME = "OtherFailingMessage_warnonce_test"

        @classmethod
        def _handle(
            cls, _event_bus: EventBus, _message: MessagePayloadType
        ) -> HandlingResult:
            raise ValueError("simulated parse failure")

    name_a = _AlwaysRaisingMessage.NAME
    name_b = _OtherFailingMessage.NAME
    message_module._parse_failure_counts.pop(name_a, None)
    message_module._parse_failure_counts.pop(name_b, None)

    event_bus = Mock(spec_set=EventBus)

    with caplog.at_level(logging.DEBUG, logger="deebot_client.message"):
        # Burn through threshold for A
        for i in range(_PARSE_FAILURE_THRESHOLD + 1):
            _AlwaysRaisingMessage.handle(event_bus, {"a": i})
        # B should still warn the first time
        _OtherFailingMessage.handle(event_bus, {"b": "first"})

    b_warnings = [
        r
        for r in caplog.records
        if r.levelname == "WARNING" and name_b in r.getMessage()
    ]
    assert len(b_warnings) == 1, "Sibling NAME must remain at WARNING level"
