import pytest

from deebot_client.commands.clean_logs import GetCleanLogs
from deebot_client.commands.error import GetError
from deebot_client.message import Message
from deebot_client.messages import get_message
from deebot_client.messages.battery import OnBattery


@pytest.mark.parametrize(
    "name, expected",
    [
        ("onBattery", OnBattery),
        ("onBattery_V2", OnBattery),
        ("onError", GetError),
        ("GetCleanLogs", GetCleanLogs),
        ("unknown", None),
    ],
)
def test_get_messages(name: str, expected: type[Message] | None) -> None:
    """Test get messages."""
    assert get_message(name) == expected
