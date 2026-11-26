"""Tests regarding child lock commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.commands.json import GetChildLock, SetChildLock
from deebot_client.commands.json.child_lock import NgiotGetChildLock, NgiotSetChildLock
from deebot_client.events import ChildLockEvent
from tests.helpers import get_request_json, get_success_body

from . import (
    assert_command,
    assert_ngiot_invalid_query_data,
    assert_ngiot_query,
    assert_ngiot_write_and_read_back,
    assert_set_enable_command,
)

if TYPE_CHECKING:
    from unittest.mock import Mock

    from deebot_client.models import ApiDeviceInfo


@pytest.mark.parametrize("value", [False, True])
async def test_GetChildLock(*, value: bool) -> None:
    """Testing get child lock."""
    json, firmware_event = get_request_json(get_success_body({"on": 1 if value else 0}))
    await assert_command(GetChildLock(), json, (firmware_event, ChildLockEvent(value)))


@pytest.mark.parametrize("value", [False, True])
async def test_SetChildLock(*, value: bool) -> None:
    """Testing set child lock."""
    await assert_set_enable_command(
        SetChildLock(value), ChildLockEvent, enabled=value, field_name="on"
    )


@pytest.mark.parametrize("value", [False, True])
@pytest.mark.parametrize("code", [0, "0"])
async def test_ngiot_query(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    value: bool,
    code: int | str,
) -> None:
    await assert_ngiot_query(
        authenticator,
        api_device_info,
        event_bus_mock,
        NgiotGetChildLock(),
        "childLock",
        value,
        ChildLockEvent(value),
        code,
    )


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"childLock": None},
        {"childLock": "false"},
        {"childLock": 0},
    ],
)
async def test_ngiot_invalid_query_data(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    data: dict[str, Any],
) -> None:
    await assert_ngiot_invalid_query_data(
        authenticator, api_device_info, event_bus_mock, NgiotGetChildLock(), data
    )


@pytest.mark.parametrize(("requested", "reported"), [(False, False), (True, True)])
@pytest.mark.parametrize("code", [0, "0"])
async def test_ngiot_write_and_read_back(
    authenticator: Mock,
    api_device_info: ApiDeviceInfo,
    event_bus_mock: Mock,
    requested: bool,
    reported: bool,
    code: int | str,
) -> None:
    await assert_ngiot_write_and_read_back(
        authenticator,
        api_device_info,
        event_bus_mock,
        NgiotSetChildLock(requested),
        "50038",
        "childLock",
        requested,
        reported,
        ChildLockEvent(reported),
        code,
    )


@pytest.mark.parametrize("enable", [0, 1, "false", None])
def test_ngiot_invalid_child_lock(enable: Any) -> None:
    with pytest.raises(TypeError, match="Child lock must be"):
        NgiotSetChildLock(enable)
