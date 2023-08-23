import pytest

from deebot_client.commands.json.error import GetError
from deebot_client.const import DataType
from deebot_client.message import Message
from deebot_client.messages import get_message
from deebot_client.messages.json.battery import OnBattery


@pytest.mark.parametrize(
    "name, expected",
    [
        ("onBattery", OnBattery),
        ("onBattery_V2", OnBattery),
        ("onError", GetError),
        ("GetCleanLogs", None),
        ("unknown", None),
    ],
)
def test_get_messages(name: str, expected: type[Message] | None) -> None:
    """Test get messages."""
    assert get_message(name, DataType.JSON) == expected
