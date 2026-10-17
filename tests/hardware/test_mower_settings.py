from __future__ import annotations

from deebot_client.commands.json import COMMANDS
from deebot_client.commands.json.animal_protection import (
    GetAnimalProtection,
    SetAnimalProtection,
)
from deebot_client.commands.json.humanoid_ai import GetHumanoidAi, SetHumanoidAi
from deebot_client.commands.json.narrow_adapt import GetNarrowAdapt, SetNarrowAdapt
from deebot_client.commands.json.recognization import (
    GetRecognization,
    SetRecognization,
)
from deebot_client.commands.json.volume import GetVolume, SetFallVolume, SetVolume
from deebot_client.events import (
    AiRecognitionEvent,
    AnimalProtectionEvent,
    FallVolumeEvent,
    HumanoidAiEvent,
    NarrowAdaptEvent,
    VolumeEvent,
)
from deebot_client.hardware import get_static_device_info
from deebot_client.messages import get_message
from deebot_client.messages.json import (
    OnAnimalProtection,
    OnHumanoidAi,
    OnMoveUpWarning,
    OnNarrowAdapt,
    OnRecognization,
    OnVolume,
)


async def test_mower_settings_capabilities() -> None:
    device_info = await get_static_device_info("2i0fns")
    assert device_info is not None
    settings = device_info.capabilities.settings

    expected = [
        (
            settings.ai_recognition,
            AiRecognitionEvent,
            GetRecognization,
            SetRecognization,
        ),
        (settings.humanoid_ai, HumanoidAiEvent, GetHumanoidAi, SetHumanoidAi),
        (settings.narrow_adapt, NarrowAdaptEvent, GetNarrowAdapt, SetNarrowAdapt),
        (
            settings.animal_protection,
            AnimalProtectionEvent,
            GetAnimalProtection,
            SetAnimalProtection,
        ),
        (settings.fall_volume, FallVolumeEvent, GetVolume, SetFallVolume),
    ]
    for capability, event, get_command, set_command in expected:
        assert capability is not None
        assert capability.event is event
        assert capability.get == [get_command()]
        assert capability.set is set_command

    assert settings.volume is not None
    assert settings.volume.event is VolumeEvent
    assert settings.volume.get == [GetVolume()]
    assert settings.volume.set(6) == SetVolume(6, channel="sys", total=10)


async def test_mower_settings_registration() -> None:
    device_info = await get_static_device_info("2i0fns")
    assert device_info is not None

    for command in (
        GetRecognization,
        SetRecognization,
        GetHumanoidAi,
        SetHumanoidAi,
        GetNarrowAdapt,
        SetNarrowAdapt,
        GetAnimalProtection,
        SetAnimalProtection,
    ):
        assert COMMANDS[command.NAME] is command

    for message in (
        OnRecognization,
        OnHumanoidAi,
        OnNarrowAdapt,
        OnMoveUpWarning,
        OnAnimalProtection,
        OnVolume,
    ):
        assert get_message(message.NAME, device_info) is message


async def test_mower_settings_are_model_specific() -> None:
    device_info = await get_static_device_info("yna5xi")
    assert device_info is not None
    settings = device_info.capabilities.settings

    assert settings.ai_recognition is None
    assert settings.animal_protection is None
    assert settings.humanoid_ai is None
    assert settings.narrow_adapt is None
    assert settings.fall_volume is None
