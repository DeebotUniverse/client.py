from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.events import (
    AiRecognitionEvent,
    AnimalProtectionEvent,
    FallVolumeEvent,
    FirmwareEvent,
    HumanoidAiEvent,
    MoveUpWarningEvent,
    NarrowAdaptEvent,
    VolumeEvent,
)
from deebot_client.messages.json import (
    OnAnimalProtection,
    OnHumanoidAi,
    OnMoveUpWarning,
    OnNarrowAdapt,
    OnRecognization,
    OnVolume,
)
from tests.messages.json import assert_message

if TYPE_CHECKING:
    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("message", "payload", "event"),
    [
        (OnRecognization, {"state": 1}, AiRecognitionEvent(True)),
        (OnHumanoidAi, {"enable": 0}, HumanoidAiEvent(False)),
        (OnNarrowAdapt, {"state": 1}, NarrowAdaptEvent(True)),
        (OnMoveUpWarning, {"enable": 1}, MoveUpWarningEvent(True)),
        (
            OnAnimalProtection,
            {"enable": 1, "start": "22:00", "end": "6:30"},
            AnimalProtectionEvent(True, "22:00", "06:30"),
        ),
    ],
)
def test_mower_setting_push(
    message: type, payload: dict[str, int | str], event: Event
) -> None:
    data = {"header": {"fwVer": "1.13.10"}, "body": {"data": payload}}
    assert_message(message, data, (FirmwareEvent("1.13.10"), event))


def test_volume_push() -> None:
    data = {
        "header": {"fwVer": "1.13.10"},
        "body": {
            "data": {
                "total": 10,
                "volume": 5,
                "fallVolume": 2,
                "searchVolume": 10,
            }
        },
    }
    assert_message(
        OnVolume,
        data,
        (FirmwareEvent("1.13.10"), VolumeEvent(5, 10), FallVolumeEvent(2, 10)),
    )
