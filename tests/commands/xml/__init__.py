from functools import partial
from typing import Any

from deebot_client.hardware.deebot import get_static_device_info
from tests.commands import assert_command as assert_command_base

assert_command = partial(
    assert_command_base, static_device_info=get_static_device_info("ls1ok3")
)


def get_request_xml(data: str | None) -> dict[str, Any]:
    return {"id": "ALZf", "ret": "ok", "resp": data, "payloadType": "x"}
