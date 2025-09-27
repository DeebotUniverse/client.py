from __future__ import annotations

import pytest

from deebot_client.command import Command, CommandResult
from deebot_client.commands.xml import (
    GetMapM,
    GetMapSet,
    GetMapSt,
    GetTrM,
    PullM,
    PullMP,
)
from deebot_client.events import (
    CachedMapInfoEvent,
    MajorMapEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MinorMapEvent,
)
from deebot_client.events.map import Map
from deebot_client.message import HandlingState
from tests.commands.xml import get_request_xml

from . import assert_command


@pytest.mark.parametrize(
    ("built_flag", "expected_built"),
    [
        ("built", True),
        ("not built", False),
    ],
    ids=["built", "not_built"],
)
async def test_GetMapSt(built_flag: str, expected_built: bool) -> None:
    json = get_request_xml(f"<ctl ret='ok' st='{built_flag}' method='auto'/>")
    await assert_command(
        GetMapSt(),
        json,
        CachedMapInfoEvent({Map("", "", using=True, built=expected_built)}),
        command_result=CommandResult(
            HandlingState.SUCCESS, None, [GetMapSet(t) for t in MapSetType]
        ),
    )


@pytest.mark.parametrize(
    "xml",
    ["<ctl ret='error'/>", "<ctl ret='ok'/>"],
    ids=["error", "no_state"],
)
async def test_GetMapSt_error(xml: str) -> None:
    json = get_request_xml(xml)
    await assert_command(
        GetMapSt(),
        json,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )


@pytest.mark.parametrize(
    ("xml", "map_type", "subsets"),
    [
        (
            '<ctl ret="ok" tp="vw" msid="1"><m mid="1" p="1" /><m mid="2" p="1" /></ctl>',
            MapSetType.VIRTUAL_WALLS,
            [1, 2],
        ),
        (
            '<ctl ret="ok" tp="ar" msid="1" />',
            MapSetType.ROOMS.value,
            [],
        ),
        (
            '<ctl ret="ok" tp="mw" msid="1" ><m p="1" /><m mid="3" p="1" /></ctl>',
            MapSetType.NO_MOP_ZONES.value,
            [3],
        ),
    ],
    ids=["virtual_walls", "rooms", "no_mop"],
)
async def test_GetMapSet(
    xml: str, map_type: MapSetType | str, subsets: list[int]
) -> None:
    json = get_request_xml(xml)
    type_as_enum, type_as_str = (
        (map_type, map_type.value)
        if isinstance(map_type, MapSetType)
        else (MapSetType(map_type), map_type)
    )
    requested_commands: list[Command] = [
        PullM(mid=subset, msid="1", type=type_as_enum) for subset in subsets
    ]
    await assert_command(
        GetMapSet(map_type),
        json,
        MapSetEvent(
            map_type if isinstance(map_type, MapSetType) else MapSetType(map_type),
            subsets=subsets,
        ),
        command_result=CommandResult(
            HandlingState.SUCCESS,
            args={
                GetMapSet._ARGS_MSID: "1",
                GetMapSet._ARGS_TYPE: type_as_str,
                GetMapSet._ARGS_SUBSETS: subsets,
            },
            requested_commands=requested_commands,
        ),
    )


@pytest.mark.parametrize(
    "xml",
    [
        "<ctl ret='error'/>",
        "<ctl ret='ok'/>",
        "<ctl ret='ok' msid='1'/>",
        "<ctl ret='ok' tp='mw'/>",
        '<ctl ret="ok" tp="???" msid="1" />',
    ],
    ids=["error", "no_state_1", "no_state_2", "no_state_3", "invalid_type"],
)
async def test_GetMapSet_error(xml: str) -> None:
    json = get_request_xml(xml)
    await assert_command(
        GetMapSet("unused"),
        json,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )


@pytest.mark.parametrize(
    ("index", "map_hash"),
    [
        ("1245233875", [1295764014, 1295764014]),
    ],
    ids=["success"],
)
async def test_GetMapM(index: str, map_hash: list[int]) -> None:
    json = get_request_xml(
        f'<ctl i="{index}" w="100" h="100" r="8" c="8" p="50" m="{",".join([str(x) for x in map_hash])}"/>'
    )
    await assert_command(
        GetMapM(),
        json,
        MajorMapEvent(index, values=map_hash, requested=True),
    )


@pytest.mark.parametrize(
    "xml",
    [
        "<ctl />",
        "<ctl i='1'/>",
        "<ctl m='42'/>",
    ],
    ids=["no_state_1", "no_state_2", "no_state_3"],
)
async def test_GetMapM_error(xml: str) -> None:
    json = get_request_xml(xml)
    await assert_command(
        GetMapM(),
        json,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )


@pytest.mark.parametrize(
    ("coordinates", "map_type"),
    [
        ("[751,-960,751,-1242,1118,-1242,1118,-960]", MapSetType.ROOMS),
        (
            "-3000,-4400;-3000,-3650;-2450,-3500;-2450,-2400;-2350,-2300;-2350,-1500;-1750,-1500;-1650,-1600;-1250,-1550;-1250,-2300;-1350,-2300;-1600,-2550;-1500,-2750;-1500,-3850;-1750,-3850;-2100,-4200;-2100,-4450;-2150,-4400;-3000,-4400",
            MapSetType.VIRTUAL_WALLS.value,
        ),
    ],
    ids=["array_data", "string_data"],
)
async def test_PullM(coordinates: str, map_type: MapSetType | str) -> None:
    json = get_request_xml(f"<ctl ret='ok' m='{coordinates}'/>")
    map_type_enum = (
        map_type if isinstance(map_type, MapSetType) else MapSetType(map_type)
    )
    expected_event = MapSubsetEvent(id=1, type=map_type_enum, coordinates=coordinates)
    await assert_command(
        PullM(mid=1, msid=2, type=map_type),
        json,
        expected_event,
        command_result=CommandResult(
            HandlingState.SUCCESS, {PullM._ARG_COORDS: expected_event.coordinates}
        ),
    )


@pytest.mark.parametrize(
    "xml",
    [
        "<ctl ret='error'/>",
        "<ctl ret='ok'/>",
    ],
    ids=["error", "no_state"],
)
async def test_PullM_error(xml: str) -> None:
    json = get_request_xml(xml)
    await assert_command(
        PullM(mid=1, msid=1),
        json,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )


@pytest.mark.parametrize(
    ("xml", "expected_event"),
    [("<ctl ret='ok' p='base64data' />", MinorMapEvent(index=1, value="base64data"))],
    ids=["base64_data"],
)
async def test_PullMP(xml: str, expected_event: MinorMapEvent) -> None:
    json = get_request_xml(xml)
    await assert_command(
        PullMP(piece_index=1),
        json,
        expected_event,
        command_result=CommandResult(
            HandlingState.SUCCESS, {PullMP._ARG_PIECE: expected_event.value}
        ),
    )


@pytest.mark.parametrize(
    "xml",
    [
        "<ctl ret='error'/>",
        "<ctl ret='ok'/>",
    ],
    ids=["error", "no_state"],
)
async def test_PullMP_error(xml: str) -> None:
    json = get_request_xml(xml)
    await assert_command(
        PullMP(piece_index=1),
        json,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )


@pytest.mark.parametrize(
    "xml",
    ["<ctl ret='ok'/>"],
    ids=["trace_enabled"],
)
async def test_GetTrM(xml: str) -> None:
    json = get_request_xml(xml)
    await assert_command(
        GetTrM(),
        json,
        None,
    )


@pytest.mark.parametrize(
    "xml",
    ["<ctl ret='error'/>"],
    ids=["error"],
)
async def test_GetTrM_error(xml: str) -> None:
    json = get_request_xml(xml)
    await assert_command(
        GetTrM(),
        json,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )
