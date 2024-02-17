from __future__ import annotations

from deebot_client.commands.json import COMMANDS


def test_all_commands_4_abstract_methods() -> None:
    # Verify that all abstract methods are implemented
    for commands in COMMANDS.values():
        implemented_methods = set(commands.__dict__.keys())
        assert getattr(commands, "__abstractmethods__", set()).issubset(
            implemented_methods
        )
