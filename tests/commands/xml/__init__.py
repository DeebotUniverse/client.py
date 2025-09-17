from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from xml.etree.ElementTree import Element, SubElement

from defusedxml import ElementTree  # type: ignore[import-untyped]
from testfixtures import LogCapture

from deebot_client.command import Command, CommandResult
from deebot_client.message import HandlingState
from tests.commands import assert_command as assert_command_base

if TYPE_CHECKING:
    from collections.abc import Sequence

    from deebot_client.commands.xml.common import ExecuteCommand
    from deebot_client.events import Event


async def assert_command(
    command: Command,
    json_api_response: dict[str, Any] | tuple[dict[str, Any], ...],
    expected_events: Event | None | Sequence[Event],
    *,
    device_class: str = "2pv572",
    command_result: CommandResult | None = None,
    expected_raw_response: dict[str, Any] | None = None,
) -> None:
    await assert_command_base(
        command,
        json_api_response,
        expected_events,
        device_class=device_class,
        command_result=command_result,
        expected_raw_response=expected_raw_response,
    )


def get_success_body(
    extra_attrs: dict[str, Any] | None = None, sub_element_name: str | None = None
) -> str:
    element = ctl_element = Element("ctl")
    element.set("ret", "ok")

    if extra_attrs is not None and len(extra_attrs) > 0:
        if sub_element_name is not None:
            element = SubElement(element, sub_element_name.lower())

        if isinstance(extra_attrs, dict):
            for key, value in extra_attrs.items():
                element.set(key, value)

    return cast("str", ElementTree.tostring(ctl_element, "unicode"))


def get_failure_body() -> str:
    return '<ctl ret="error" />'


async def assert_execute_command(
    command: ExecuteCommand, args: dict[str, Any] | list[Any] | None
) -> None:
    assert command.NAME != "invalid"
    assert command._args == args

    # success
    xml = get_request_xml(get_success_body())
    await assert_command(command, xml, None)

    # failed
    with LogCapture() as log:
        body = get_failure_body()
        xml = get_request_xml(body)
        await assert_command(
            command, xml, None, command_result=CommandResult(HandlingState.FAILED)
        )

        log.check_present(
            (
                "deebot_client.commands.xml.common",
                "WARNING",
                f'Command "{command.NAME}" was not successful. XML response: {body}',
            )
        )


def get_request_xml(data: str | None) -> dict[str, Any]:
    return {"id": "ALZf", "ret": "ok", "resp": data, "payloadType": "x"}
