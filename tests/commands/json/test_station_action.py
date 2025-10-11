"""Auto empty tests."""

from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands import StationAction
from deebot_client.commands.json import station_action

from . import assert_execute_command


@pytest.mark.parametrize(
    ("action", "args"),
    [
        (
            StationAction.EMPTY_DUSTBIN,
            {"act": 1, "type": 1},
        ),
    ],
)
async def test_StationAction(
    action: StationAction,
    args: dict[str, Any],
) -> None:
    """Test StationAction."""
    command = station_action.StationAction(action)
    await assert_execute_command(command, args)
