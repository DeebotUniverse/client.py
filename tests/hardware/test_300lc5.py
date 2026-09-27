from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, cast

import pytest

from deebot_client.capabilities import DeviceType
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import CleanAreaMower, CleanMower, GetCleanInfo
from deebot_client.commands.json.error import GetError
from deebot_client.event_bus import EventBus
from deebot_client.events import ErrorEvent, StateEvent
from deebot_client.hardware import get_static_device_info
from deebot_client.messages import get_message
from deebot_client.models import CleanAction, State

if TYPE_CHECKING:
    from unittest.mock import Mock

    from deebot_client.authentication import Authenticator
    from deebot_client.command import Command
    from deebot_client.models import ApiDeviceInfo


async def test_300lc5_mower_controls() -> None:
    info = await get_static_device_info("300lc5")
    assert info is not None
    capabilities = info.capabilities

    assert capabilities.device_type is DeviceType.MOWER
    assert capabilities.clean.action.command is CleanMower
    assert capabilities.clean.action.area is CleanAreaMower
    assert capabilities.charge.execute is Charge
    assert Charge()._args == {"act": "go"}
    assert capabilities.state.get == [GetChargeState(), GetCleanInfo()]


async def test_300lc5_state_refresh_recovers_mowing(
    authenticator: Authenticator, api_device_info: ApiDeviceInfo
) -> None:
    """Use the O500's supported query to replace a stale error with activity."""
    info = await get_static_device_info("300lc5")
    assert info is not None

    # Issue #936: the O500 answers getCleanInfo, but getCleanInfo_V2 times out.
    responses = {
        "getChargeState": {"isCharging": 0},
        "getCleanInfo": {
            "trigger": "app",
            "state": "clean",
            "cleanState": {"motionState": "working", "content": {"type": "auto"}},
        },
    }

    async def respond(
        _path: str, payload: dict[str, Any], **_kwargs: Any
    ) -> dict[str, Any]:
        if data := responses.get(payload["cmdName"]):
            return {"ret": "ok", "resp": {"body": {"code": 0, "data": data}}}
        return {"ret": "fail", "errno": 500}

    cast("Mock", authenticator.post_authenticated).side_effect = respond

    async def execute(command: Command) -> dict[str, Any]:
        return (
            await command.execute(authenticator, api_device_info, events)
        ).raw_response

    events = EventBus(execute, info.capabilities)
    events.notify(StateEvent(State.ERROR))
    try:
        for command in info.capabilities.state.get:
            await execute(command)
        assert events.get_last_event(StateEvent) == StateEvent(State.CLEANING)
    finally:
        await events.teardown()


@pytest.mark.parametrize(
    "trigger", ["clean_ack", "charge_ack", "error_clear", "charge_idle"]
)
async def test_300lc5_recovery_after_in_flight_poll(  # noqa: PLR0915 - exercise the full command/event race
    authenticator: Authenticator, api_device_info: ApiDeviceInfo, trigger: str
) -> None:
    """A pre-control snapshot must not consume the post-control refresh."""
    info = await get_static_device_info("300lc5")
    assert info is not None
    started = asyncio.Event()
    release = asyncio.Event()
    updated = asyncio.Event()
    queries = 0

    async def respond(
        _path: str, payload: dict[str, Any], **_kwargs: Any
    ) -> dict[str, Any]:
        nonlocal queries
        name = payload["cmdName"]
        if name == "getCleanInfo":
            queries += 1
            if queries == 1:
                started.set()
                await release.wait()
                data: dict[str, Any] = {"state": "idle"}
            else:
                data = {"state": "clean", "cleanState": {"motionState": "working"}}
        elif name == "getChargeState":
            data = {"isCharging": 0}
        elif name in {"clean", "charge"}:
            return {"ret": "ok", "resp": {"body": {"code": 0}}}
        else:
            pytest.fail(f"Unexpected command: {name}")
        return {"ret": "ok", "resp": {"body": {"code": 0, "data": data}}}

    cast("Mock", authenticator.post_authenticated).side_effect = respond

    async def execute(command: Command) -> dict[str, Any]:
        return (
            await command.execute(authenticator, api_device_info, events)
        ).raw_response

    async def on_state(event: StateEvent) -> None:
        if event.state is State.CLEANING:
            updated.set()

    events = EventBus(execute, info.capabilities)
    events.notify(StateEvent(State.ERROR))
    events.subscribe(StateEvent, on_state)
    try:
        events.request_refresh(StateEvent)
        await asyncio.wait_for(started.wait(), 1)
        if trigger == "clean_ack":
            await execute(CleanMower(CleanAction.START))
        elif trigger == "charge_ack":
            await execute(Charge())
        elif trigger == "error_clear":
            GetError.handle(events, {"body": {"data": {"code": []}}})
        else:
            handler = get_message("onChargeInfo", info)
            assert handler is not None
            handler.handle(events, {"body": {"data": {"state": "idle"}}})
        await asyncio.sleep(0)
        release.set()
        await asyncio.wait_for(updated.wait(), 1)
        assert events.get_last_event(StateEvent) == StateEvent(State.CLEANING)
        assert queries == 2
    finally:
        await events.teardown()


@pytest.mark.parametrize("trigger", ["clean_ack", "error_clear", "charge_idle"])
@pytest.mark.parametrize("charging", [False, True])
async def test_300lc5_recovery_queries_real_activity(
    authenticator: Authenticator,
    api_device_info: ApiDeviceInfo,
    trigger: str,
    charging: bool,
) -> None:
    """Exercise message/control recovery through the real event-bus refresh."""
    info = await get_static_device_info("300lc5")
    assert info is not None
    queried: list[str] = []
    expected = State.DOCKED if charging else State.CLEANING
    updated = asyncio.Event()

    async def respond(
        _path: str, payload: dict[str, Any], **_kwargs: Any
    ) -> dict[str, Any]:
        name = payload["cmdName"]
        queried.append(name)
        if name == "getChargeState":
            data: dict[str, Any] = {"isCharging": int(charging)}
        elif name == "getCleanInfo":
            data = (
                {"state": "idle"}
                if charging
                else {"state": "clean", "cleanState": {"motionState": "working"}}
            )
        elif name == "clean":
            return {"ret": "ok", "resp": {"body": {"code": 0}}}
        else:
            return {"ret": "fail", "errno": 500}
        return {"ret": "ok", "resp": {"body": {"code": 0, "data": data}}}

    cast("Mock", authenticator.post_authenticated).side_effect = respond

    async def execute(command: Command) -> dict[str, Any]:
        return (
            await command.execute(authenticator, api_device_info, events)
        ).raw_response

    async def on_state(event: StateEvent) -> None:
        if event.state is expected:
            updated.set()

    events = EventBus(execute, info.capabilities)
    events.notify(StateEvent(State.ERROR))
    events.notify(ErrorEvent(105, "synthetic fault"))
    events.subscribe(StateEvent, on_state)
    try:
        if trigger == "clean_ack":
            await execute(CleanMower(CleanAction.START))
        elif trigger == "error_clear":
            GetError.handle(events, {"body": {"data": {"code": []}}})
        else:
            handler = get_message("onChargeInfo", info)
            assert handler is not None
            handler.handle(events, {"body": {"data": {"state": "idle"}}})
        await asyncio.wait_for(updated.wait(), 1)
        assert events.get_last_event(StateEvent) == StateEvent(expected)
        assert "getChargeState" in queried
        assert "getCleanInfo" in queried
        assert "getCleanInfo_V2" not in queried
    finally:
        await events.teardown()
