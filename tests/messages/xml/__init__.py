from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.message import (
    HandlingResult,
    HandlingState,
    Message,
    MessagePayloadType,
)
from tests.messages import assert_message as _assert_message

if TYPE_CHECKING:
    from collections.abc import Sequence

    from deebot_client.events import Event


async def assert_message(
    message: type[Message],
    data: MessagePayloadType,
    expected_events: Event | None | Sequence[Event],
    *,
    device_class: str = "2pv572",
    expected_state: HandlingState = HandlingState.SUCCESS,
) -> HandlingResult:
    return await _assert_message(
        message,
        data,
        expected_events,
        device_class=device_class,
        expected_state=expected_state,
    )
