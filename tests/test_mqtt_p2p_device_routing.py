from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from deebot_client.const import DataType
from deebot_client.mqtt_client import MqttClient, MqttConfiguration

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator


def _create_client(authenticator: Authenticator) -> MqttClient:
    """Create MQTT client for P2P routing tests."""
    return MqttClient(
        MqttConfiguration(
            hostname="localhost",
            port=1883,
            ssl_context=None,
            device_id="test",
        ),
        authenticator,
    )


def test_p2p_request_uses_receiver_device(
    authenticator: Authenticator,
) -> None:
    """Test P2P requests use the receiver device for command lookup."""
    client = _create_client(authenticator)

    topic_split = [
        "iot",
        "p2p",
        "setVolume",
        "sender-did",
        "sender-class",
        "sender-resource",
        "receiver-did",
        "receiver-class",
        "receiver-resource",
        "q",
        "request-id",
        "j",
    ]

    with patch.object(
        client,
        "_get_p2p_command_type",
        return_value=None,
    ) as command_lookup:
        client._handle_p2p(topic_split, b"{}")

    command_lookup.assert_called_once_with(
        "setVolume",
        DataType.JSON,
        "receiver-did",
    )


def test_p2p_response_uses_sender_device(
    authenticator: Authenticator,
) -> None:
    """Test P2P responses use the sender device for command lookup."""
    client = _create_client(authenticator)

    topic_split = [
        "iot",
        "p2p",
        "setVolume",
        "sender-did",
        "sender-class",
        "sender-resource",
        "receiver-did",
        "receiver-class",
        "receiver-resource",
        "p",
        "request-id",
        "j",
    ]

    with patch.object(
        client,
        "_get_p2p_command_type",
        return_value=None,
    ) as command_lookup:
        client._handle_p2p(topic_split, b"{}")

    command_lookup.assert_called_once_with(
        "setVolume",
        DataType.JSON,
        "sender-did",
    )
