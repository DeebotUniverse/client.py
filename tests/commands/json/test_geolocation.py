"""Tests regarding geolocation and play sound commands."""

from __future__ import annotations

import pytest

from deebot_client.commands.json import GetGeolocation, PlaySound, SetGeolocation
from deebot_client.commands.json.play_sound import PlayAlarmSound
from deebot_client.events import GeolocationEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_execute_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetGeolocation(*, value: bool) -> None:
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "enable": 1 if value else 0,
                "geoLocation": {"longitude": "1.0", "latitude": "2.0"},
            }
        )
    )
    await assert_command(
        GetGeolocation(), json, (firmware_event, GeolocationEvent(value))
    )


@pytest.mark.parametrize("value", [False, True])
async def test_SetGeolocation(*, value: bool) -> None:
    await assert_set_enable_command(
        SetGeolocation(value), GeolocationEvent, enabled=value
    )


async def test_PlaySound() -> None:
    await assert_execute_command(PlaySound(), {"count": 1, "sid": 30})
    await assert_execute_command(PlayAlarmSound(), {"count": 1, "sid": 51})
