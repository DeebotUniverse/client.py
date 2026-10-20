from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from deebot_client.capabilities import CapabilityCleanAction
from deebot_client.command import Command
from deebot_client.commands.json.clean import GetCleanInfo, GoatClean, GoatCleanArea
from deebot_client.event_bus import EventBus
from deebot_client.events import GoatCleanModeEvent, StateEvent
from deebot_client.hardware import get_static_device_info
from deebot_client.models import CleanAction, CleanMode, State


async def test_o1200_advertises_mower_clean_commands() -> None:
    info = await get_static_device_info("2i0fns")
    assert info is not None
    capabilities = info.capabilities.clean.action

    assert isinstance(capabilities, CapabilityCleanAction)
    assert capabilities.command is GoatClean
    assert capabilities.area is GoatCleanArea


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        (
            CleanAction.START,
            {"act": "start", "content": {"type": "auto"}},
        ),
        (
            CleanAction.PAUSE,
            {"act": "pause", "content": {"type": "auto"}},
        ),
        (
            CleanAction.RESUME,
            {"act": "resume", "content": {"type": "auto"}},
        ),
        (
            CleanAction.STOP,
            {"act": "stop", "content": {"type": "auto"}},
        ),
    ],
)
def test_o1200_actions_match_observed_clean_payload(
    action: CleanAction, expected: dict[str, object]
) -> None:
    command = GoatClean(action)

    assert command.NAME == "clean"
    assert command.NAME != "clean_V2"
    assert command._args == expected


def test_o1200_sentrum_area_start_matches_observed_payload() -> None:
    command = GoatCleanArea(CleanMode.SPOT_AREA, [1])

    assert command.NAME == "clean"
    assert command._args == {
        "act": "start",
        "content": {"type": "spotArea", "value": "1"},
    }


def test_o1200_area_serialization_does_not_guess_multi_area_format() -> None:
    with pytest.raises(ValueError, match="integer area IDs"):
        GoatCleanArea(CleanMode.SPOT_AREA, [])


def test_o1200_multi_area_start_preserves_order() -> None:
    command = GoatCleanArea(CleanMode.SPOT_AREA, [1, 2])

    assert command._args == {
        "act": "start",
        "content": {"type": "spotArea", "value": "1,2"},
    }


def test_o1200_area_command_rejects_non_spot_mode() -> None:
    with pytest.raises(ValueError, match="spotArea mode"):
        GoatCleanArea(CleanMode.FREE_CLEAN, [1])


def test_o1200_area_command_rejects_unsupported_cleanings() -> None:
    with pytest.raises(ValueError, match="exactly one cleaning"):
        GoatCleanArea(CleanMode.SPOT_AREA, [1], cleanings=2)


async def test_o1200_start_state_switch_keeps_goat_payload() -> None:
    event_bus = Mock(spec_set=EventBus)

    def get_last_event(event_type: type[object]) -> object:
        if event_type is GoatCleanModeEvent:
            return GoatCleanModeEvent("spotArea")
        return StateEvent(State.PAUSED)

    event_bus.get_last_event.side_effect = get_last_event
    command = GoatClean(CleanAction.START)

    # The state-aware base implementation changes START to RESUME.
    with patch.object(Command, "_execute", new=AsyncMock()):
        await command._execute(Mock(), Mock(), event_bus)

    assert command._args == {
        "act": "resume",
        "content": {"type": "spotArea"},
    }


async def test_o1200_malformed_args_fall_back_to_start() -> None:
    event_bus = Mock(spec_set=EventBus)
    event_bus.get_last_event.return_value = None
    command = GoatClean(CleanAction.START)
    command._args = {}

    with patch.object(Command, "_execute", new=AsyncMock()):
        await command._execute(Mock(), Mock(), event_bus)

    assert command._args == {
        "act": "start",
        "content": {"type": "auto"},
    }


async def test_o1200_explicit_mode_skips_mode_resolution() -> None:
    event_bus = Mock(spec_set=EventBus)
    command = GoatClean(CleanAction.PAUSE, mode=CleanMode.SPOT_AREA)

    with patch.object(Command, "_execute", new=AsyncMock()):
        await command._execute(Mock(), Mock(), event_bus)

    event_bus.get_last_event.assert_called_once_with(StateEvent)
    assert command._args == {
        "act": "pause",
        "content": {"type": "spotArea"},
    }


def test_o1200_area_non_start_has_no_value() -> None:
    command = GoatCleanArea(CleanMode.SPOT_AREA, [1, 2])

    assert command._get_args(CleanAction.PAUSE) == {
        "act": "pause",
        "content": {"type": "spotArea"},
    }


async def test_o1200_new_start_ignores_stale_area_mode() -> None:
    event_bus = Mock(spec_set=EventBus)

    def get_last_event(event_type: type[object]) -> object:
        if event_type is GoatCleanModeEvent:
            return GoatCleanModeEvent("spotArea")
        return StateEvent(State.CLEANING)

    event_bus.get_last_event.side_effect = get_last_event
    command = GoatClean(CleanAction.START)

    with patch.object(Command, "_execute", new=AsyncMock()):
        await command._execute(Mock(), Mock(), event_bus)

    assert command._args == {
        "act": "start",
        "content": {"type": "auto"},
    }


@pytest.mark.parametrize("mode", [CleanMode.AUTO, CleanMode.SPOT_AREA])
@pytest.mark.parametrize(
    "action", [CleanAction.PAUSE, CleanAction.RESUME, CleanAction.STOP]
)
async def test_o1200_controls_follow_observed_active_mode(
    mode: CleanMode, action: CleanAction
) -> None:
    event_bus = Mock(spec_set=EventBus)
    event_bus.get_last_event.side_effect = lambda event_type: (
        GoatCleanModeEvent(mode.value) if event_type is GoatCleanModeEvent else None
    )
    command = GoatClean(action)

    with patch.object(Command, "_execute", new=AsyncMock()):
        await command._execute(Mock(), Mock(), event_bus)

    assert command._args == {
        "act": action.value,
        "content": {"type": mode.value},
    }


@pytest.mark.parametrize("mode", ["auto", "spotArea"])
def test_clean_info_records_observed_goat_mode(mode: str) -> None:
    event_bus = Mock(spec_set=EventBus)
    event_bus.capabilities = Mock(device_type="mower")

    GetCleanInfo._handle_body_data_dict(
        event_bus,
        {
            "state": "clean",
            "cleanState": {
                "motionState": "working",
                "content": {"type": mode, "value": "1,2"},
            },
        },
    )

    assert event_bus.notify.call_args_list[0].args == (GoatCleanModeEvent(mode),)
