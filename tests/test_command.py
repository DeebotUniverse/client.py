from typing import Any

import pytest

from deebot_client.command import CommandMqttP2P, InitParam
from deebot_client.exceptions import DeebotError


class _TestCommand(CommandMqttP2P):
    name = "TestCommand"
    _mqtt_params = {"field": InitParam(int)}


def test_CommandMqttP2P_no_mqtt_params() -> None:
    class TestCommandNoParams(CommandMqttP2P):
        pass

    with pytest.raises(DeebotError, match=r"_mqtt_params not set"):
        TestCommandNoParams.create_from_mqtt({})


@pytest.mark.parametrize(
    "data, expected",
    [
        ({"field": "a"}, r"""Could not convert "a" of field into <class 'int'>"""),
        ({"something": "a"}, r'"field" is missing in {\'something\': \'a\'}'),
    ],
)
def test_CommandMqttP2P_create_from_mqtt_error(
    data: dict[str, Any], expected: str
) -> None:
    with pytest.raises(DeebotError, match=expected):
        _TestCommand.create_from_mqtt(data)
