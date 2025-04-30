from __future__ import annotations

from types import MappingProxyType
from typing import Any
from unittest.mock import Mock, patch

import pytest

from deebot_client.command import CommandResult, InitParam
from deebot_client.commands.xml.common import XmlCommandMqttP2P
from deebot_client.event_bus import EventBus
from deebot_client.events import LifeSpan


@pytest.mark.parametrize(
    ("payload", "decoded_payload"),
    [
        (bytearray(bytes("test", "utf-8")), "test"),
        (bytes("test", "utf-8"), "test"),
        ("test", "test"),
    ],
    ids=["bytearray", "bytes", "str"],
)
@patch.multiple(XmlCommandMqttP2P, __abstractmethods__=set())
def test_XmlCommandMqttP2P_decoding(
    payload: bytearray | bytes | str, decoded_payload: str
) -> None:
    command = XmlCommandMqttP2P()  # type: ignore[abstract]
    event_bus = Mock(spec_set=EventBus)
    with patch.object(command, "_handle_mqtt_p2p", return_value=None) as mqtt_handler:
        command.handle_mqtt_p2p(event_bus, payload)

    mqtt_handler.assert_called_once_with(event_bus, decoded_payload)


@patch.multiple(XmlCommandMqttP2P, __abstractmethods__=set())
def test_XmlCommandMqttP2P_invalid_decoding() -> None:
    command = XmlCommandMqttP2P()  # type: ignore[abstract]
    event_bus = Mock(spec_set=EventBus)
    with (
        patch.object(command, "_handle_mqtt_p2p", return_value=None),
        pytest.raises(TypeError),
    ):
        command.handle_mqtt_p2p(event_bus, {})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("command_payload", "payload_type", "expected_argument"),
    [
        ("test", str, "test"),
        (LifeSpan.BRUSH.xml_value, LifeSpan, LifeSpan.BRUSH),
    ],
    ids=["native", "with xml_value"],
)
def test_XmlCommandMqttP2P_create_from_mqtt(
    command_payload: str, payload_type: type, expected_argument: type
) -> None:
    class Sut(XmlCommandMqttP2P):
        NAME = "Sut"
        _mqtt_params = MappingProxyType(
            {"payload": InitParam(payload_type), "remove": None}
        )

        def __init__(self, payload: Any) -> None:
            super().__init__(args={"payload": payload})

        def _handle_mqtt_p2p(
            self, _event_bus: EventBus, _response: dict[str, Any] | str
        ) -> None:
            pass

        def _handle_response(
            self, _event_bus: EventBus, _response: dict[str, Any]
        ) -> CommandResult:
            return CommandResult.analyse()

    xml_message = f"<ctl ret='ok' payload='{command_payload}' remove='42' />"

    sut = Sut.create_from_mqtt(xml_message)

    assert sut._args == {"payload": expected_argument}
