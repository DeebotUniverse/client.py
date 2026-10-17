from __future__ import annotations

import pytest

from deebot_client.commands.json import (
    GetAnimalProtection,
    GetHumanoidAi,
    GetNarrowAdapt,
    GetRecognization,
    SetAnimalProtection,
    SetHumanoidAi,
    SetNarrowAdapt,
    SetRecognization,
)
from deebot_client.events import (
    AiRecognitionEvent,
    AnimalProtectionEvent,
    HumanoidAiEvent,
    NarrowAdaptEvent,
)
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_command, assert_set_enable_command


@pytest.mark.parametrize(
    ("get_command", "set_command", "event_type", "field_name"),
    [
        (GetRecognization, SetRecognization, AiRecognitionEvent, "state"),
        (GetHumanoidAi, SetHumanoidAi, HumanoidAiEvent, "enable"),
        (GetNarrowAdapt, SetNarrowAdapt, NarrowAdaptEvent, "state"),
    ],
)
@pytest.mark.parametrize("enabled", [False, True])
async def test_enable_settings(
    get_command: type,
    set_command: type,
    event_type: type,
    field_name: str,
    *,
    enabled: bool,
) -> None:
    json, firmware_event = get_request_json(
        get_success_body({field_name: int(enabled)})
    )
    await assert_command(get_command(), json, (firmware_event, event_type(enabled)))
    await assert_set_enable_command(
        set_command(enabled), event_type, enabled=enabled, field_name=field_name
    )


async def test_animal_protection() -> None:
    json, firmware_event = get_request_json(
        get_success_body({"enable": 1, "start": "23:45", "end": "6:30"})
    )
    event = AnimalProtectionEvent(True, "23:45", "06:30")
    await assert_command(GetAnimalProtection(), json, (firmware_event, event))
    await assert_set_command(
        SetAnimalProtection(True, "23:45", "6:30"),
        {"enable": 1, "start": "23:45", "end": "06:30"},
        event,
    )
