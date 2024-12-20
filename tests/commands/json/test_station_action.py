"""Auto empty tests."""

from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands import BaseStationAction
from deebot_client.commands.json.station_action import StationAction

from . import assert_execute_command


@pytest.mark.parametrize(
    ("action", "args"),
    [
        (
            BaseStationAction.EMPTY_DUSTBIN,
            {"act": 1, "type": 1},
        ),
    ],
)
async def test_StationAction(
    action: BaseStationAction,
    args: dict[str, Any],
) -> None:
    """Test StationAction."""
    command = StationAction(action)
    await assert_execute_command(command, args)
