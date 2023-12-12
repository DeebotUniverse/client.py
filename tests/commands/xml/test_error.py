from deebot_client.commands.xml import GetError
from deebot_client.events import ErrorEvent

from . import assert_command, get_request_xml


async def test_getErrors() -> None:
    json = get_request_xml("<ctl ret='ok' errs=''/>")
    await assert_command(
        GetError(), json, ErrorEvent(0, "NoError: Robot is operational")
    )
