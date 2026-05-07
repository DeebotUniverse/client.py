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


@pytest.fixture
def _reset_parse_failure_counts() -> None:
    message_module._parse_failure_counts.clear()


class _AlwaysRaisingMessage(Message):
    NAME = "AlwaysRaisingMessage_warnonce_test"

    @classmethod
    def _handle(
        cls, _event_bus: EventBus, _message: MessagePayloadType
    ) -> HandlingResult:
        raise ValueError("simulated parse failure")


class _OtherFailingMessage(Message):
    NAME = "OtherFailingMessage_warnonce_test"

    @classmethod
    def _handle(
        cls, _event_bus: EventBus, _message: MessagePayloadType
    ) -> HandlingResult:
        raise ValueError("simulated parse failure")


@pytest.mark.usefixtures("_reset_parse_failure_counts")
def test_warn_once_throttles_repeated_parse_failures(
    caplog: pytest.LogCaptureFixture,
) -> None:
    name = _AlwaysRaisingMessage.NAME
    event_bus = Mock(spec_set=EventBus)
    logger_name = "deebot_client.message"

    with caplog.at_level(logging.DEBUG, logger=logger_name):
        for i in range(_PARSE_FAILURE_THRESHOLD + 2):
            assert (
                _AlwaysRaisingMessage.handle(event_bus, {"i": i}).state
                == HandlingState.ERROR
            )

    assert [
        (
            logger_name,
            logging.WARNING,
            f"Could not parse {name}: {{'i': 0}}",
        ),
        (
            logger_name,
            logging.WARNING,
            f"Could not parse {name}: {{'i': 1}}",
        ),
        (
            logger_name,
            logging.WARNING,
            f"Could not parse {name}: {{'i': 2}}",
        ),
        (
            logger_name,
            logging.WARNING,
            f"Further 'Could not parse {name}' entries will be logged at DEBUG level",
        ),
        (
            logger_name,
            logging.DEBUG,
            f"Could not parse {name}: {{'i': 3}}",
        ),
        (
            logger_name,
            logging.DEBUG,
            f"Could not parse {name}: {{'i': 4}}",
        ),
    ] == caplog.record_tuples


@pytest.mark.usefixtures("_reset_parse_failure_counts")
def test_warn_once_isolated_per_message_name(
    caplog: pytest.LogCaptureFixture,
) -> None:
    name_a = _AlwaysRaisingMessage.NAME
    name_b = _OtherFailingMessage.NAME
    event_bus = Mock(spec_set=EventBus)
    logger_name = "deebot_client.message"

    with caplog.at_level(logging.DEBUG, logger=logger_name):
        for i in range(_PARSE_FAILURE_THRESHOLD + 1):
            _AlwaysRaisingMessage.handle(event_bus, {"a": i})
        _OtherFailingMessage.handle(event_bus, {"b": "first"})

    assert [
        (
            logger_name,
            logging.WARNING,
            f"Could not parse {name_a}: {{'a': 0}}",
        ),
        (
            logger_name,
            logging.WARNING,
            f"Could not parse {name_a}: {{'a': 1}}",
        ),
        (
            logger_name,
            logging.WARNING,
            f"Could not parse {name_a}: {{'a': 2}}",
        ),
        (
            logger_name,
            logging.WARNING,
            f"Further 'Could not parse {name_a}' entries will be logged at DEBUG level",
        ),
        (
            logger_name,
            logging.DEBUG,
            f"Could not parse {name_a}: {{'a': 3}}",
        ),
        (
            logger_name,
            logging.WARNING,
            f"Could not parse {name_b}: {{'b': 'first'}}",
        ),
    ] == caplog.record_tuples
