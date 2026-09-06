"""Station action tests."""

from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands import StationAction
from deebot_client.commands.json import station_action
from deebot_client.commands.json.xwk78e import StationActionT80

from . import assert_execute_command


@pytest.mark.parametrize(
    ("action", "args"),
    [
        (
            StationAction.EMPTY_DUSTBIN,
            {"act": 1, "type": 1},
        ),
        (
            StationAction.DRY_MOP,
            {"act": 1, "type": 2},
        ),
        (
            StationAction.CLEAN_BASE,
            {"act": 1, "type": 3},
        ),
    ],
)
async def test_StationAction(
    action: StationAction,
    args: dict[str, Any],
) -> None:
    """Test the shared station action command."""
    await assert_execute_command(station_action.StationAction(action), args)


@pytest.mark.parametrize("act", [1, 2, 3, 4])
async def test_StationActionT80(act: int) -> None:
    """Test T80 station actions with explicit action verbs."""
    await assert_execute_command(
        StationActionT80(StationAction.WASH_MOP, act=act),
        {"act": act, "type": 4},
    )
