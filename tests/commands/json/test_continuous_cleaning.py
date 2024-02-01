from __future__ import annotations

import pytest

from deebot_client.commands.json import GetContinuousCleaning, SetContinuousCleaning
from deebot_client.events import ContinuousCleaningEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetContinuousCleaning(*, value: bool) -> None:
    json = get_request_json(get_success_body({"enable": 1 if value else 0}))
    await assert_command(GetContinuousCleaning(), json, ContinuousCleaningEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetContinuousCleaning(*, value: bool) -> None:
    await assert_set_enable_command(
        SetContinuousCleaning(value), ContinuousCleaningEvent, enabled=value
    )
