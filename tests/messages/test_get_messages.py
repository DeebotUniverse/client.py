import pytest

from deebot_client.commands.json.error import GetError
from deebot_client.const import DataType
from deebot_client.message import Message
from deebot_client.messages import get_message
from deebot_client.messages.json.battery import OnBattery


@pytest.mark.parametrize(
    "name, data_type, expected",
    [
        ("onBattery", DataType.JSON, OnBattery),
        ("onBattery_V2", DataType.JSON, OnBattery),
        ("onError", DataType.JSON, GetError),
        ("GetCleanLogs", DataType.JSON, None),
        ("unknown", DataType.JSON, None),
        ("unknown", DataType.XML, None),
    ],
)
def test_get_messages(
    name: str, data_type: DataType, expected: type[Message] | None
) -> None:
    """Test get messages."""
    assert get_message(name, data_type) == expected
