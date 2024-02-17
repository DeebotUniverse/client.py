from __future__ import annotations

from deebot_client.messages.json import MESSAGES


def test_all_messages_4_abstract_methods() -> None:
    # Verify that all abstract methods are implemented
    for messages in MESSAGES.values():
        implemented_methods = set(messages.__dict__.keys())
        assert getattr(messages, "__abstractmethods__", set()).issubset(
            implemented_methods
        )
