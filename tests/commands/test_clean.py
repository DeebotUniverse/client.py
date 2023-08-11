from typing import Any
from unittest.mock import Mock

import pytest

from deebot_client.authentication import Authenticator
from deebot_client.commands import GetCleanInfo
from deebot_client.commands.clean import Clean, CleanAction
from deebot_client.events import StateEvent
from deebot_client.events.event_bus import EventBus
from deebot_client.models import DeviceInfo, VacuumState
from tests.commands import assert_command
from tests.helpers import get_request_json, get_request_xml


@pytest.mark.parametrize(
    "json, expected",
    [
        (
            get_request_json({"trigger": "none", "state": "idle"}),
            StateEvent(VacuumState.IDLE),
        ),
    ],
)
async def test_GetCleanInfo(json: dict[str, Any], expected: StateEvent) -> None:
    await assert_command(GetCleanInfo(), json, expected)


@pytest.mark.parametrize(
    "response, expected",
    [
        (
            get_request_xml(
                "<ctl ret='ok'><clean type='auto' speed='standard' st='h' t='134' a='0' s='1691787964' tr=''/></ctl>"
            ),
            StateEvent(VacuumState.IDLE),
        ),
        (
            get_request_xml(
                "<ctl ret='ok'><clean type='auto' speed='standard' st='p' t='27' a='0' s='1691787964' tr=''/></ctl>"
            ),
            StateEvent(VacuumState.PAUSED),
        ),
        (
            get_request_xml(
                "<ctl ret='ok'><clean type='auto' speed='standard' st='s' t='40' a='0' s='1691787964' tr=''/></ctl>"
            ),
            StateEvent(VacuumState.CLEANING),
        ),
        (
            get_request_xml(
                "<ctl ret='ok'><clean type='auto' speed='standard' st='h' t='134' a='1' s='1691787964' tr=''/></ctl>"
            ),
            StateEvent(VacuumState.RETURNING),
        ),
    ],
)
async def test_GetCleanInfoXml(response: dict[str, Any], expected: StateEvent) -> None:
    await assert_command(GetCleanInfo(), response, expected)


@pytest.mark.parametrize(
    "action, vacuum_state, expected",
    [
        (CleanAction.START, None, CleanAction.START),
        (CleanAction.START, VacuumState.PAUSED, CleanAction.RESUME),
        (CleanAction.START, VacuumState.DOCKED, CleanAction.START),
        (CleanAction.RESUME, None, CleanAction.RESUME),
        (CleanAction.RESUME, VacuumState.PAUSED, CleanAction.RESUME),
        (CleanAction.RESUME, VacuumState.DOCKED, CleanAction.START),
    ],
)
async def test_Clean_act(
    authenticator: Authenticator,
    device_info: DeviceInfo,
    action: CleanAction,
    vacuum_state: VacuumState | None,
    expected: CleanAction,
) -> None:
    event_bus = Mock(spec_set=EventBus)
    event_bus.get_last_event.return_value = (
        StateEvent(vacuum_state) if vacuum_state is not None else None
    )
    command = Clean(action)

    await command.execute(authenticator, device_info, event_bus)

    assert isinstance(command._args, dict)
    assert command._args["act"] == expected.value
